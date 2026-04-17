---
name: research-batch-processor
description: Run research-note-router across every file in docs/research/ and docs/research/roadmap/, aggregate findings, and execute approved actions in batch
---

# Purpose

Process a directory of research notes through the router, present an aggregated plan, get operator approval once, then execute all routing actions.

# Workflow

## Phase 1: Discovery

1. List all `*.md` files in `docs/research/` and `docs/research/roadmap/`
2. Skip `README.md` and `inbox.md`
3. Report the file list to the operator with count

## Phase 2: Analysis (per file, no action)

For each file, run `research-note-router` through Section 7 only. Do NOT execute Section 8.

Collect per-file:
- Forced Classification
- Final Verdict
- Proposed artifacts (count of specs, prompts, issues)
- Any pre-flight flags (inaccessible URLs, duplication matches)

## Phase 3: Aggregated Report

Present to operator in this format:

- BATCH RESULTS header with N files processed
- AUTO-EXECUTE section listing M files with no flags, one line per file showing the routing summary (e.g., `adversarial-dev.md -> spec X, prompt Y, 2 issues`)
- NEEDS REVIEW section listing P files with flags raised, one line per file explaining the flag
- SKIP section listing Q files classified as redundant/low-value or reference-only

## Phase 4: Single approval gate

Ask the operator ONCE:

`Proceed with AUTO-EXECUTE batch? (y/n/review-each)`

- `y` — execute Section 8 for every AUTO-EXECUTE file
- `n` — stop, report nothing executed
- `review-each` — prompt per-file for the AUTO-EXECUTE list

Files in NEEDS REVIEW always prompt individually regardless of the answer above.
Files in SKIP execute their move/archive action without additional prompt (low risk).

## Phase 5: Execution

Run Section 8 of the router for every approved file. Collect:
- files created
- files modified
- issues created (with URLs)
- errors encountered

## Phase 6: Final report

Emit a single summary:

- EXECUTION COMPLETE header
- Files created count + list
- Files modified count + list
- Issues created count + list with URLs and labels
- Errors count + list with file and error
- Next suggested action based on priorities of created issues (pick one labeled `now` + `ready`)

# Guardrails

- Never process more than 20 files without explicit confirmation
- If more than 3 files raise pre-flight flags, stop and ask operator to review the flags before continuing the batch
- If `gh` CLI is not authenticated, stop before Phase 5 and report
- Log every action to `docs/research/.batch-log-{timestamp}.md` for rollback reference
- If any individual file execution fails, record the error and continue with the remaining files. Do not abort the batch on a single failure.

# Invocation

Typical operator prompt:

`Use research-batch-processor on docs/research/`

Or scoped to a subdirectory:

`Use research-batch-processor on docs/research/roadmap/`