# beliefs

Structured knowledge base for LLM agents. Tracks claims with provenance, detects staleness, records contradictions, and provides the foundation for deep code analysis when combined with [code-expert](https://github.com/benthomasson/code-expert) and [reasons](https://github.com/benthomasson/ftl-reasons) (RMS).

## What it enables

On its own, `beliefs` gives agents a persistent, queryable knowledge base with source hashes, staleness detection, and contradiction tracking. Combined with code-expert and an RMS, it enables something more powerful: **systematic architectural analysis that finds issues code review misses.**

In one session on a 15k-line infrastructure framework, this pipeline explored 152 code topics, extracted 785 beliefs, derived logical consequences across the belief network, and surfaced architectural issues — disabled SSH host key verification, command injection vectors, a dormant policy engine — that led to 8 merged PRs and 8 closed GitHub issues. These weren't bugs in diffs. They were design-level gaps with no single commit that introduced them.

The belief registry is the structured layer that makes this possible. Individual observations ("known_hosts=None") become tracked facts. Facts connect via dependencies. Dependencies enable derivation. Derivation surfaces contradictions. Contradictions become actionable issues.

## Quick Start

```bash
pip install ftl-beliefs
cd ~/git/my-repo
beliefs install-skill
claude
```

Then inside Claude Code:

```
/beliefs init
```

## Problem

LLM agents have no persistent memory structure. CLAUDE.md files go stale, claims get retracted without dependents being updated, and contradictions survive context compaction. Agents cannot distinguish between a belief formed yesterday and one formed six months ago, or tell that a later finding supersedes an earlier one.

`beliefs` is a practical approximation of classical truth maintenance (ATMS, AGM) adapted for markdown-based agent workflows. It tracks what you believe, where each belief comes from, and what depends on what — so when something changes, you know what else must change.

## Install

No dependencies beyond Python 3.10+ standard library.

```bash
# Install from PyPI
pip install ftl-beliefs

# Or with uv
uv tool install ftl-beliefs

# Or run without installing
uvx ftl-beliefs nogoods
```

## Usage

### Initialize a registry

```bash
# Create beliefs.md and nogoods.md in the current directory
beliefs init

# With repos for cross-reference resolution
beliefs init --repos myproject shared-lib:~/code/shared-lib
```

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

- **Markdown, not YAML/JSON.** The registry is useful without the CLI — an LLM or human can read `beliefs.md` directly. Ablation experiments (6 versions) show that grep over beliefs.md outperforms structured database lookup by 6-11pp for Sonnet — the flat format provides contextual clustering that isolated records lack.
- **Keyword heuristics, not NLP.** Staleness detection uses keyword overlap and negation patterns. Crude but independent of the system being verified.
- **STALE, not auto-retract.** The tool flags problems for human review. It never changes IN to OUT automatically. For automatic retraction cascades, pair with [reasons](https://github.com/benthomasson/ftl-reasons) (RMS).
- **Nogoods are append-only.** Contradictions survive context compaction and session boundaries.
- **Zero dependencies.** Python 3.10+ standard library only. No LLM calls, no database, no server.

## Ecosystem

`beliefs` is one layer in a stack for structured AI reasoning:

| Tool | Role | Repo |
|------|------|------|
| **beliefs** | Structured knowledge base with provenance and staleness detection | [beliefs](https://github.com/benthomasson/beliefs) |
| **reasons** (RMS) | Dependency-directed truth maintenance with automatic retraction cascades | [ftl-reasons](https://github.com/benthomasson/ftl-reasons) |
| **code-expert** | Deep code analysis — scan, explore, extract beliefs, derive, file issues | [code-expert](https://github.com/benthomasson/code-expert) |
| **entry** | Chronological documentation with filesystem-encoded timestamps | [entry](https://github.com/benthomasson/entry) |

**Standalone:** `beliefs` works on its own for any project that needs persistent claim tracking with staleness detection.

**With RMS:** `reasons` adds automatic retraction cascades — retract one belief and all dependents update. Use `reasons export-markdown` to regenerate beliefs.md from the RMS database.

**With code-expert:** The full pipeline: scan a codebase → explore topics → extract beliefs → derive logical consequences → file GitHub issues from OUT gated beliefs. This is where architectural analysis happens.

## Claude Code Skill

The repo includes a [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill at `.claude/skills/beliefs/SKILL.md` that lets AI agents use the beliefs system via natural language. When the skill is loaded, an agent can:

- Run `/beliefs status` to get a full registry health check (check-refs + check-stale + compact)
- Run `/beliefs add <natural language description>` and have it converted to the right CLI flags
- Run `/beliefs show`, `/beliefs list`, `/beliefs update` with natural language arguments

The skill handles CLI discovery (installed binary → local script → uvx fallback) and interprets results — suggesting fixes for FAIL/WARN/STALE findings rather than just printing raw output.

To install the skill into any project:

```bash
# Install to .claude/skills/beliefs/SKILL.md (default)
beliefs install-skill

# Or specify a custom skills directory
beliefs install-skill --skill-dir .claude/custom-skills
```

## Origin

Built during a research program investigating whether structured belief tracking improves LLM agent performance. The program found that multi-agent LLM systems suffer from belief staleness, circular verification, and cross-repository knowledge gaps — the same problems classical AI addressed with truth maintenance systems in the 1980s. This tool bridges those two worlds.

Production knowledge bases built with this tool include 785 beliefs (ftl2-expert, infrastructure automation) and 440 beliefs (agents-python-expert, AI orchestration framework), with findings that led to merged PRs, closed issues, and retracted security vulnerabilities.

## References

The design draws on classical AI belief maintenance and belief revision literature:

- **Doyle, J. (1979).** "A Truth Maintenance System." *Artificial Intelligence*, 12(3), 231–272. [doi:10.1016/0004-3702(79)90008-0](https://doi.org/10.1016/0004-3702(79)90008-0)
  The original justification-based TMS. Introduced dependency-directed backtracking and the idea that beliefs should be retracted when their justifications fail. The `compact` command's prioritized summarization is inspired by TMS dependency tracking.

- **de Kleer, J. (1986).** "An Assumption-based TMS." *Artificial Intelligence*, 28(2), 127–162. [doi:10.1016/0004-3702(86)90080-9](https://doi.org/10.1016/0004-3702(86)90080-9)
  The assumption-based TMS (ATMS). Tracks multiple simultaneous worldviews via assumption sets. The `nogoods` database and `assumes` metadata on claims come directly from the ATMS design — a nogood is a set of assumptions known to be jointly inconsistent.

- **Alchourrón, C., Gärdenfors, P., & Makinson, D. (1985).** "On the Logic of Theory Change: Partial Meet Contraction and Revision Functions." *Journal of Symbolic Logic*, 50(2), 510–530. [doi:10.2307/2274239](https://doi.org/10.2307/2274239)
  The AGM framework for belief revision. Defines contraction (removing a belief with minimal disruption), revision (adding a belief while maintaining consistency), and expansion. The `resolve` command's entrenchment ordering implements AGM's epistemic entrenchment — more entrenched beliefs are harder to retract.

- **Gärdenfors, P. (1988).** *Knowledge in Flux: Modeling the Dynamics of Epistemic States.* MIT Press. [ISBN 978-0-262-07109-3](https://www.amazon.com/dp/0262071096)
  Book-length treatment of AGM theory with epistemic entrenchment ordering. The entrenchment scoring system (`resolve`) — source priority + recency bonus + derivation type — is a practical approximation of Gärdenfors's formal ordering.

- **Forbus, K. & de Kleer, J. (1993).** *Building Problem Solvers.* MIT Press. [ISBN 978-0-262-06157-5](https://mitpress.mit.edu/9780262528153/building-problem-solvers/)
  Comprehensive treatment of TMS/ATMS implementation with cross-system dependency tracking. The multi-repository cross-reference checking (`check-refs`, `depends-on`) follows the pattern of inter-system dependency management described here.

- **McCarthy, J. & Hayes, P. (1969).** "Some Philosophical Problems from the Standpoint of Artificial Intelligence." *Machine Intelligence*, 4, 463–502. [PDF](http://www-formal.stanford.edu/jmc/mcchay69.pdf)
  Introduced the frame problem: how to efficiently represent what *doesn't* change when an action occurs. The `check-stale` command addresses the LLM version of the frame problem — when a source file changes, which claims are still valid and which need updating?
