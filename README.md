# beliefs

A CLI tool for tracking claims and contradictions across multi-agent LLM research systems.

## Problem

When multiple LLM agents work across repositories, their beliefs diverge. CLAUDE.md files go stale, claims get retracted without dependents being updated, and contradictions survive context compaction. Current LLMs have no mechanism for maintaining consistency across a knowledge base as beliefs change over time.

`beliefs` is a practical approximation of classical truth maintenance (ATMS, AGM) adapted for markdown-based agent workflows. It tracks what you believe, where each belief comes from, and what depends on what — so when something changes, you know what else must change.

## Install

No dependencies beyond Python 3.10+ standard library.

```bash
# Run directly with uvx (no install needed)
uvx --from git+https://github.com/benthomasson/beliefs beliefs nogoods

# Or install with uv/pip
uv tool install git+https://github.com/benthomasson/beliefs
pip install git+https://github.com/benthomasson/beliefs

# Or clone and run directly
git clone https://github.com/benthomasson/beliefs && cd beliefs
./beliefs nogoods
```

## Usage

### Track claims

```bash
# Add a claim with source, assumptions, and dependencies
beliefs add \
    --id auth-uses-jwt \
    --text "Authentication switched from sessions to JWT tokens" \
    --source backend/entries/2025/03/15/auth-refactor.md \
    --assumes stateless-api \
    --depends-on api-v2-design \
    --type DERIVED
```

### Detect problems

```bash
# Check that cited sources exist and are consistent
beliefs check-refs

# Find IN claims contradicted by newer entries
beliefs check-stale
```

### Resolve conflicts

```bash
# Compare entrenchment scores to determine which claim wins
beliefs resolve old-claim new-claim
```

### Query contradictions

```bash
# List all recorded contradictions
beliefs nogoods

# Find contradictions affecting a specific claim
beliefs nogoods --affecting some-claim-id
```

### Generate context summaries

```bash
# Produce a belief state summary within a token budget
beliefs compact --budget 500
```

## Data Files

**`beliefs.md`** — The claim registry. Each claim has an ID, status (IN/OUT/STALE), source file, date, assumptions, and dependencies. Hand-editable; readable without the CLI.

**`nogoods.md`** — The contradiction database. Append-only. Records what went wrong, when, and what it affected. Never delete a nogood.

## Six Operations

| Command | What it does | Classical source |
|---|---|---|
| `add` | Register a claim with assumptions and dependencies | ATMS (de Kleer 1986) |
| `resolve` | Resolve conflicts via entrenchment ordering | AGM (Gardenfors 1988) |
| `nogoods` | Query the persistent contradiction database | ATMS (de Kleer 1986) |
| `check-stale` | Detect claims contradicted by newer entries | Frame problem (McCarthy 1969) |
| `check-refs` | Verify source files exist and are consistent | Cross-reference verification |
| `compact` | Produce a dependency-aware context summary | TMS summarization (Doyle 1979) |

## Design Choices

- **Markdown, not YAML/JSON.** The registry is useful without the CLI — an LLM or human can read `beliefs.md` directly.
- **Keyword heuristics, not NLP.** Staleness detection uses keyword overlap and negation patterns. Crude but independent of the system being verified.
- **STALE, not auto-retract.** The tool flags problems for human review. It never changes IN to OUT automatically.
- **Nogoods are append-only.** Contradictions survive context compaction and session boundaries.
- **Zero dependencies.** Python 3.10+ standard library only. No LLM calls, no database, no server.

## Origin

Built as a proof-of-concept during a meta-research study on using AI for open-ended research. The study found that multi-agent LLM systems suffer from belief staleness, circular verification, and cross-repository knowledge gaps — the same problems classical AI addressed with truth maintenance systems in the 1980s. This tool bridges those two worlds.
