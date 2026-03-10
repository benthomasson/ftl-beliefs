"""Contradiction detection among IN beliefs.

Finds pairs of IN beliefs that may contradict each other using:
1. Embedding similarity (if fastembed available) — fast semantic matching
2. Keyword overlap fallback — groups beliefs sharing keywords

Optionally verifies candidates with an LLM judge.
"""

import os
import re
import subprocess

from . import Claim
from .check_refs import extract_keywords

# Pairs that suggest opposing claims when both appear
OPPOSITION_MARKERS = [
    ("always", "never"),
    ("required", "optional"),
    ("must", "must not"),
    ("synchronous", "asynchronous"),
    ("single", "multiple"),
    ("direct", "indirect"),
    ("before", "after"),
    ("internal", "external"),
    ("stateless", "stateful"),
    ("mutable", "immutable"),
    ("blocks", "does not block"),
    ("raises", "does not raise"),
    ("returns", "does not return"),
]


def _keyword_similarity(claims: list[Claim], min_overlap: int = 3) -> list[tuple[Claim, Claim, float]]:
    """Find claim pairs with high keyword overlap."""
    keyword_map = {}
    for claim in claims:
        keyword_map[claim.id] = set(extract_keywords(claim.text))

    pairs = []
    claim_list = list(claims)
    for i in range(len(claim_list)):
        for j in range(i + 1, len(claim_list)):
            a, b = claim_list[i], claim_list[j]
            ka, kb = keyword_map[a.id], keyword_map[b.id]
            overlap = len(ka & kb)
            if overlap >= min_overlap:
                union = len(ka | kb)
                score = overlap / union if union else 0
                pairs.append((a, b, score))

    pairs.sort(key=lambda x: x[2], reverse=True)
    return pairs


def _check_opposition(text_a: str, text_b: str) -> list[str]:
    """Check if two texts contain opposing language."""
    a_lower = text_a.lower()
    b_lower = text_b.lower()
    found = []
    for pos, neg in OPPOSITION_MARKERS:
        if (pos in a_lower and neg in b_lower) or (neg in a_lower and pos in b_lower):
            found.append(f"{pos}/{neg}")
    return found


def _embedding_similarity(claims: list[Claim], threshold: float = 0.7) -> list[tuple[Claim, Claim, float]]:
    """Find semantically similar claim pairs using embeddings."""
    try:
        from fastembed import TextEmbedding
        import numpy as np
    except ImportError:
        return []

    model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    texts = [c.text for c in claims]
    embeddings = list(model.embed(texts))
    matrix = np.array(embeddings)

    # Normalize for cosine similarity
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1
    matrix = matrix / norms

    pairs = []
    for i in range(len(claims)):
        for j in range(i + 1, len(claims)):
            sim = float(np.dot(matrix[i], matrix[j]))
            if sim >= threshold:
                pairs.append((claims[i], claims[j], sim))

    pairs.sort(key=lambda x: x[2], reverse=True)
    return pairs


def _llm_verify(claim_a: Claim, claim_b: Claim, model: str = "claude") -> tuple[bool, str]:
    """Use LLM to check whether two similar beliefs actually contradict."""
    prompt = f"""\
Two beliefs are held simultaneously in a knowledge base. Determine whether they contradict each other.

Belief A ({claim_a.id}): {claim_a.text}
Belief B ({claim_b.id}): {claim_b.text}

Consider:
- Do they make incompatible claims about the same thing?
- Could both be true simultaneously (e.g., about different contexts)?
- Is one a refinement or specialization of the other (not a contradiction)?

Respond with exactly one line:
VERDICT: CONTRADICTION or COMPATIBLE
Then one line:
EXPLANATION: <brief reason>
"""
    cmd = ["claude", "-p"] if model == "claude" else ["gemini", "-p", ""]

    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    try:
        result = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True, timeout=60, env=env,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, "verify failed"

    if result.returncode != 0:
        return False, "verify failed"

    response = result.stdout
    verdict = re.search(r"VERDICT:\s*(CONTRADICTION|COMPATIBLE)", response, re.IGNORECASE)
    explanation = re.search(r"EXPLANATION:\s*(.+)", response, re.IGNORECASE)

    if not verdict:
        return False, "no verdict"

    is_contradiction = verdict.group(1).upper() == "CONTRADICTION"
    reason = explanation.group(1).strip() if explanation else ""
    return is_contradiction, reason


def find_contradictions(
    claims: list[Claim],
    threshold: float = 0.7,
    min_keyword_overlap: int = 3,
    verify: bool = False,
    model: str = "claude",
) -> list[dict]:
    """Find potentially contradicting IN belief pairs.

    Args:
        claims: List of claims (only IN claims will be checked)
        threshold: Embedding similarity threshold (0.0-1.0)
        min_keyword_overlap: Minimum shared keywords for keyword fallback
        verify: Whether to use LLM to verify contradictions
        model: Model name for LLM verification

    Returns:
        List of dicts with keys: claim_a, claim_b, score, method, opposition,
        verified (if verify=True), explanation (if verify=True)
    """
    in_claims = [c for c in claims if c.status == "IN"]
    if len(in_claims) < 2:
        return []

    # Try embeddings first, fall back to keywords
    pairs = _embedding_similarity(in_claims, threshold)
    method = "embedding"
    if not pairs:
        pairs = _keyword_similarity(in_claims, min_keyword_overlap)
        method = "keyword"

    results = []
    for claim_a, claim_b, score in pairs:
        opposition = _check_opposition(claim_a.text, claim_b.text)

        entry = {
            "claim_a": claim_a,
            "claim_b": claim_b,
            "score": score,
            "method": method,
            "opposition": opposition,
        }

        if verify:
            is_contradiction, explanation = _llm_verify(claim_a, claim_b, model)
            entry["verified"] = is_contradiction
            entry["explanation"] = explanation
        else:
            entry["verified"] = None
            entry["explanation"] = ""

        results.append(entry)

    return results
