# beliefs — Claude Code agent instructions

## What This Is

A CLI tool for tracking claims and contradictions across multi-agent LLM research systems. ~900 lines of Python, zero dependencies, operates on two markdown files: `beliefs.md` (claim registry) and `nogoods.md` (contradiction database).

## Repository Structure

```
beliefs/
├── beliefs              # CLI entry point (argparse, command dispatch)
├── beliefs.md           # Claim registry — the source of truth
├── nogoods.md           # Contradiction database — append-only
└── beliefs_lib/         # Package
    ├── __init__.py      # Claim and Nogood dataclasses
    ├── parser.py        # Markdown parse/serialize for both data files
    ├── check_refs.py    # Cross-reference verification (source exists, keywords match)
    ├── check_stale.py   # Staleness detection (newer entries contradict IN claims)
    ├── resolve.py       # Entrenchment scoring and conflict resolution
    ├── nogoods_cmd.py   # Nogood listing, filtering, ID generation
    └── compact.py       # Token-budgeted context summary generation
```

## Commands

```
beliefs check-refs          # Verify source files exist and match claim keywords
beliefs check-stale         # Find IN claims contradicted by newer entries
beliefs add --id ID --text TEXT [--source PATH] [--type TYPE] [--assumes ...] [--depends-on ...]
beliefs resolve CLAIM_A CLAIM_B   # Compare entrenchment scores
beliefs nogoods [--affecting CLAIM_ID]
beliefs compact [--budget N]      # Default budget: 500 tokens
```

Global flags: `--registry PATH` (default: `beliefs.md`), `--nogoods-file PATH` (default: `nogoods.md`), `--quiet` (exit code only). The `--quiet` flag goes before the subcommand.

## Data Model

**Claim** fields: id, text, source, date, status (IN/OUT/STALE), type (DERIVED/PREDICTED/MATCHED/INHERITED/AXIOM), assumes, depends_on, retracted_by, nogood, stale_reason, superseded_by, ref_check.

**Nogood** fields: id, description, discovered, discovered_by, resolution, affects.

## beliefs.md Format

```markdown
### claim-id [STATUS] TYPE
Claim text on one line
- Source: repo-name/path/to/file.md
- Date: YYYY-MM-DD
- Assumes: label-a, label-b
- Depends on: other-claim-id
```

The `## Repos` section maps repo names to paths (e.g., `- physics: ~/git/physics`). The parser uses these to resolve `Source:` paths to absolute filesystem paths.

## Key Algorithms

**check-refs:** For each claim, resolve the source path via the Repos map, check file exists, extract keywords from claim text (split on non-alphanumeric, drop stopwords, keep >= 3 chars), check keyword presence in source content. Also verifies depends_on targets exist and are not OUT.

**check-stale:** For each IN claim, walk `entries/YYYY/MM/DD/` dirs across all repos for dates after the claim date. Check keyword overlap (>= 2 keywords). Check negation pairs (e.g., "derived" in claim vs "not derived" in entry). Reports at most one STALE match per claim.

**resolve:** Entrenchment score = source_priority + recency_bonus + derivation_type_priority. Source priority: verifier-audit (90), simulation (80), formal-derivation (70), analytical-argument (60), entry-claim (40), claude-md-claim (30), readme-claim (20), speculation (10). Recency: 5 per month for claims < 6 months old, capped at 30. Derivation type: AXIOM (90), DERIVED (80), PREDICTED (70), MATCHED (50), INHERITED (40). Ties go to the more recent claim.

**compact:** Nogoods always included (never dropped). Then STALE claims. Then IN claims sorted by entrenchment (high to low), truncated at token budget.

## Design Principles

- **The tool never auto-retracts.** STALE is a flag for human review, not an automatic status change. Only a human or explicit `beliefs add` with retraction sets OUT.
- **Nogoods are append-only.** Add resolutions, never delete entries. They must survive context compaction.
- **beliefs.md is readable without the CLI.** Any LLM or human can read it directly. The CLI adds automation, not access.
- **Keyword heuristics, not NLP.** Staleness and ref checking use keyword matching to avoid depending on an LLM for verification (which would reintroduce hallucination risk).

## When Modifying This Code

- The parser is regex-based. The header regex uses `[ \t]+` (not `\s+`) to avoid matching across line boundaries.
- `extract_keywords()` in `check_refs.py` is shared by `check_stale.py` — changes affect both.
- The entrenchment config in `resolve.py` is the only place to adjust scoring weights.
- `check-stale` reports at most one STALE flag per claim (first evidence wins) to avoid noisy output.
- Exit codes: 0 = all OK, 1 = issues found. Used by `--quiet` mode for scripting.
