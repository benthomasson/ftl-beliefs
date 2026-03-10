"""Duplicate belief detection and consolidation suggestions.

Groups near-duplicate IN beliefs into clusters and ranks them
by entrenchment score to suggest which to keep.
"""

import re

from . import Claim
from .check_refs import extract_keywords
from .resolve import compute_entrenchment


def _keyword_jaccard(text_a: str, text_b: str) -> float:
    """Compute Jaccard similarity between keyword sets."""
    ka = set(extract_keywords(text_a))
    kb = set(extract_keywords(text_b))
    if not ka or not kb:
        return 0.0
    return len(ka & kb) / len(ka | kb)


def _embedding_groups(claims: list[Claim], threshold: float) -> list[list[Claim]]:
    """Group claims by embedding similarity using union-find."""
    try:
        from fastembed import TextEmbedding
        import numpy as np
    except ImportError:
        return []

    model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    texts = [c.text for c in claims]
    embeddings = list(model.embed(texts))
    matrix = np.array(embeddings)

    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1
    matrix = matrix / norms

    # Union-find for clustering
    parent = list(range(len(claims)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(len(claims)):
        for j in range(i + 1, len(claims)):
            sim = float(np.dot(matrix[i], matrix[j]))
            if sim >= threshold:
                union(i, j)

    # Collect groups
    groups_map: dict[int, list[int]] = {}
    for i in range(len(claims)):
        root = find(i)
        groups_map.setdefault(root, []).append(i)

    return [
        [claims[i] for i in indices]
        for indices in groups_map.values()
        if len(indices) > 1
    ]


def _keyword_groups(claims: list[Claim], threshold: float) -> list[list[Claim]]:
    """Group claims by keyword Jaccard similarity using union-find."""
    parent = list(range(len(claims)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(len(claims)):
        for j in range(i + 1, len(claims)):
            sim = _keyword_jaccard(claims[i].text, claims[j].text)
            if sim >= threshold:
                union(i, j)

    groups_map: dict[int, list[int]] = {}
    for i in range(len(claims)):
        root = find(i)
        groups_map.setdefault(root, []).append(i)

    return [
        [claims[i] for i in indices]
        for indices in groups_map.values()
        if len(indices) > 1
    ]


def find_duplicates(
    claims: list[Claim],
    threshold: float = 0.85,
    keyword_threshold: float = 0.5,
) -> list[dict]:
    """Find groups of near-duplicate IN beliefs.

    Args:
        claims: All claims (only IN will be checked)
        threshold: Embedding similarity threshold (default: 0.85, higher = stricter)
        keyword_threshold: Jaccard threshold for keyword fallback (default: 0.5)

    Returns:
        List of dicts with keys: group (list of Claims), keep (recommended Claim),
        retire (list of Claims to retire), method
    """
    in_claims = [c for c in claims if c.status == "IN"]
    if len(in_claims) < 2:
        return []

    groups = _embedding_groups(in_claims, threshold)
    method = "embedding"
    if not groups:
        groups = _keyword_groups(in_claims, keyword_threshold)
        method = "keyword"

    results = []
    for group in groups:
        # Rank by entrenchment — highest score is the one to keep
        ranked = sorted(group, key=compute_entrenchment, reverse=True)
        keep = ranked[0]
        retire = ranked[1:]

        results.append({
            "group": group,
            "keep": keep,
            "retire": retire,
            "method": method,
        })

    # Sort by group size descending
    results.sort(key=lambda r: len(r["group"]), reverse=True)
    return results
