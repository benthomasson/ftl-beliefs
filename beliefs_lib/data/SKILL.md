---
name: beliefs
description: Manage the belief registry — track claims, detect staleness, resolve conflicts, query contradictions
argument-hint: "[init|check-refs|check-stale|contradictions|deduplicate|add|add-nogood|resolve|nogoods|compact|list|show|update|hash-sources|install-skill|status] [args...]"
allowed-tools: Bash(beliefs *), Bash(./beliefs *), Bash(uvx *beliefs*), Read, Grep, Glob
---

You are managing a belief registry using the `beliefs` CLI tool. The registry tracks claims across repositories in `beliefs.md` and contradictions in `nogoods.md`.

## How to Run

Try these in order until one works:
1. `beliefs $ARGUMENTS` (if installed via uv/pip)
2. `./beliefs $ARGUMENTS` (if in the repo directory)
3. `uvx --from git+https://github.com/benthomasson/beliefs beliefs $ARGUMENTS` (fallback)

## Subcommand Behavior

### `init`
Run `beliefs init` to create `beliefs.md` and `nogoods.md` in the current directory. Use `--repos` to register repositories for cross-reference resolution. Bare names default to `~/git/<name>`; use `name:path` for explicit paths.

Example: `/beliefs init with repos myproject and shared-lib at ~/code/shared-lib`
becomes: `beliefs init --repos myproject shared-lib:~/code/shared-lib`

### No arguments or `status`
Run all three checks and summarize:
```bash
beliefs check-refs
beliefs check-stale
beliefs compact --budget 300
```
Present a brief status report: how many claims, how many OK/WARN/FAIL/STALE, and the compact summary.

### `check-refs`
Run `beliefs check-refs`. For any FAIL or WARN results, explain what's wrong and suggest fixes.

### `check-stale`
Run `beliefs check-stale`. For any STALE results, explain the contradiction found and recommend whether to update the claim or dismiss the false positive.

### `add`
Run `beliefs add` with the provided flags. If the user gives a natural language description instead of flags, convert it:
- Extract the claim ID (kebab-case the key phrase)
- Extract the claim text
- Identify the source file if mentioned
- Identify assumptions and dependencies if mentioned
- Pick the derivation type if applicable

Example: `/beliefs add The auth system now uses JWT tokens, see backend/auth-refactor.md`
becomes: `beliefs add --id auth-uses-jwt --text "The auth system now uses JWT tokens" --source backend/auth-refactor.md`

### `resolve`
Run `beliefs resolve CLAIM_A CLAIM_B`. Explain the entrenchment scores and the resolution.

### `add-nogood`
When you encounter a failure, a known-bad approach, or discover that a combination of things doesn't work, record it:

```bash
beliefs add-nogood --description "What doesn't work" --resolution "What to do instead"
```

If the user gives natural language, convert it:
- Extract the description (what failed / what's incompatible)
- Extract the resolution (what to do instead), if given
- List any affected claim IDs with `--affects`

Example: `/beliefs add-nogood Python 3.14 breaks pydantic-core, use 3.13`
becomes: `beliefs add-nogood --description "Python 3.14 incompatible with pydantic-core" --resolution "Use Python 3.13"`

**Record nogoods when:**
- An approach was tried and failed
- A tool/version/config combination is incompatible
- A workaround was needed due to a limitation
- A previously-held assumption turned out to be wrong
- A test, query, or command doesn't behave as expected

Nogoods are append-only. Never delete a nogood. Add resolutions, don't remove entries. The ID is auto-generated (nogood-NNN).

### `nogoods`
Run `beliefs nogoods` with any provided flags (e.g., `--affecting CLAIM_ID`). Summarize the results.

### `list`
Run `beliefs list` with optional `--status IN|OUT|STALE` filter. Present the results as a quick summary.

### `show`
Run `beliefs show CLAIM_ID`. Present the full claim detail.

### `update`
Run `beliefs update CLAIM_ID` with provided flags. Supports `--status`, `--stale-reason`, `--superseded-by`, `--add-assumes`, `--add-depends-on`. If the user gives natural language, convert to flags.

### `compact`
Run `beliefs compact` with any provided flags (e.g., `--budget N`, `--no-truncate`). Output the summary directly.

### `contradictions`
Run `beliefs contradictions` to find IN beliefs that may contradict each other. Uses embedding similarity if `fastembed` is installed, otherwise falls back to keyword overlap.

```bash
# Basic scan (keyword or embedding similarity)
beliefs contradictions

# Lower threshold to catch more pairs
beliefs contradictions --threshold 0.5

# Verify candidates with LLM judge
beliefs contradictions --verify
beliefs contradictions --verify --model gemini
```

If contradictions are found, suggest resolving them with `beliefs resolve` or `beliefs update --status OUT`.

### `deduplicate`
Run `beliefs deduplicate` to find groups of near-duplicate IN beliefs. Groups by embedding similarity (if fastembed available) or keyword Jaccard overlap. Ranks each group by entrenchment score and suggests which to keep.

```bash
# Preview duplicate groups
beliefs deduplicate

# Stricter matching (fewer groups)
beliefs deduplicate --threshold 0.9

# Actually retire duplicates (sets status=OUT, superseded_by=keeper)
beliefs deduplicate --apply
```

### `hash-sources`
Run `beliefs hash-sources`. This backfills SHA-256 content hashes for all claims that have a source file but no stored hash. Use `--force` to re-hash claims that already have a hash (e.g., after confirming a source change is expected and re-registering).

After hashing, `check-stale` will detect when source files change, flagging claims whose source content has diverged from what was recorded at registration time.

## After Any Command

- If claims were flagged STALE or FAIL, suggest concrete next steps
- If the user added a claim, suggest running `beliefs check-refs` to verify it
- Keep responses concise — the tool output speaks for itself
