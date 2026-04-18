# CodeGraph preflight

Use this only as an optimization layer. It is not required for the skill to function.

## Goal
When available and worth the setup cost, use CodeGraph to reduce exploratory tool calls and improve multi-file reasoning.

## Decision rules
Prefer CodeGraph when most of the following are true:
- the repo is medium or large
- the task involves architecture tracing, impact analysis, cross-file refactors, or "find how X works end-to-end"
- the task likely touches multiple subsystems
- the repo language mix is supported well enough by the available CodeGraph setup

De-prioritize or skip CodeGraph when most of the following are true:
- the repo is small
- the task is narrow and localized
- indexing overhead is likely larger than the exploration savings
- the repo or environment is not ready for CodeGraph

## Preflight sequence
1. Detect whether CodeGraph tooling is installed and runnable.
2. Detect whether an index already exists and is fresh enough.
3. Decide whether indexing is worth doing for this task.
4. If yes:
   - build or refresh the index
   - start the MCP server if needed
   - prefer CodeGraph-backed exploration for repo structure and cross-file reasoning
5. If no, or if any step fails:
   - fall back cleanly to normal git/filesystem/search exploration

## Important constraints
- Do not fail the skill just because CodeGraph is unavailable.
- Do not blindly trust index-derived answers without validating touched files directly.
- Do not spend disproportionate time on indexing for a tiny or simple change.
- If CodeGraph appears stale or inconsistent with the working tree, validate against the actual files before acting.

## What to record in the final output
Under the implementation or plan sections, briefly note:
- whether CodeGraph was used
- why it was used or skipped
- whether the run used an existing index or built/refreshed one
