# Claude Code

## Why it is interesting

Claude Code is a strong reference for **terminal-native coding agent UX**.
The important part is not the brand. It is the operator experience around repo-aware work, approvals, edits, and iterative execution.

## What appears strong

- Terminal-first workflow that fits how developers already work
- Strong feeling of repo awareness and file-level actionability
- Practical edit/apply loop instead of purely conversational output
- Good fit for plan -> implement -> inspect -> revise cycles

## What WayWarden should borrow

### 1. Repo-aware coding handoff design
When WayWarden delegates to a coding runtime, the handoff should include:
- explicit task objective
- repo context
- target files or suspected areas
- constraints and non-goals
- acceptance criteria

### 2. Approval and action boundaries
Useful patterns include:
- clear read vs write behavior
- explicit destructive-action approval
- visible summaries of intended changes
- artifact and diff visibility before merge/deploy

### 3. Minimal-friction operator loop
The coding path should make it easy to:
- inspect files
- propose edits
- run checks
- review results
- iterate quickly

### 4. Session continuity
A good coding runtime should retain enough session context to continue work without constantly rebuilding the problem from scratch.

## What not to copy

- Product-specific assumptions about model provider or pricing
- UI/branding mimicry
- Over-centralizing all work into a coding runtime

WayWarden still needs clean EA-core boundaries and explicit runtime separation.

## Best OSS / implementation direction

Look for OSS projects that provide:
- terminal-native agent workflows
- repo-aware planning and edits
- approval gates
- session rewind/checkpointing
- clear artifact and diff presentation

The best result will likely come from combining several OSS patterns rather than copying one proprietary flow.

## Relevance to WayWarden

High for the future coding-runtime side.
Medium for the EA core.

## Recommendation

Keep Claude Code as a top-tier reference for:
- terminal UX
- coding handoff ergonomics
- approval boundaries
- fast iterative repair loops

This should influence the coding-runtime roadmap more than the immediate EA milestone.
