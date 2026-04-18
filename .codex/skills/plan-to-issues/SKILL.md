---
name: plan-to-issues
description: Convert planning docs into a normalized GitHub EPIC and child-issue set with explicit scope, non-goals, acceptance criteria, required tests, dependencies, and an execution order that a follow-on implementation skill can consume reliably.
---

# Plan To Issues

Use this skill when the user has planning docs and wants a GitHub-ready EPIC plus child issues that are structured for reliable autonomous implementation.

## Inputs
- One planning document, planning folder, spec bundle, roadmap, or execution plan.
- Optionally, repo context and existing issue conventions.

## Output contract
Use the final output format in `assets/output-format.md`.

## Workflow

1. Read the planning material fully.
2. Identify the real work slices.
3. Split them into ordered child issues that are:
   - independently actionable
   - appropriately sized
   - dependency-aware
   - testable
4. Draft a parent EPIC using `assets/epic-template.md`.
5. Draft child issues using `assets/child-issue-template.md`.
6. Apply the chunking rules in `assets/chunking-rules.md`.
7. Normalize naming, acceptance criteria, required tests, and non-goals.
8. Flag ambiguity or missing detail that would make implementation unreliable.
9. Produce the issue set ready for creation in GitHub.

## Non-negotiable rules
- Do not create vague implementation issues.
- Do not create child issues without explicit acceptance criteria.
- Do not create child issues without required tests.
- Do not hide major ambiguity inside generic wording.
- Keep each child issue small enough to be implemented and adversarially reviewed in one focused run.
- Preserve stated boundaries and non-goals from the planning docs.

## Chunking behavior
Follow `assets/chunking-rules.md`.

Default preference:
- thin vertical slices
- explicit boundaries
- one issue = one meaningful capability or one tight cleanup slice
- avoid mixing unrelated concerns just to reduce issue count

## Issue authoring behavior
Every child issue should include:
- Goal
- Scope
- Non-goals
- Acceptance criteria
- Required tests
- Blocking dependencies
- Notes when needed

Every EPIC should include:
- Goal
- ordered execution checklist
- global constraints
- definition of done

## Reliability standard
The generated issue set should be structured so a separate execution skill can safely determine the next actionable issue without guessing.

That means:
- stable naming
- explicit ordering
- dependency clarity
- concrete completion criteria

## If the plan is weak
If the planning docs are too vague to produce reliable issues:
- say so clearly
- identify the missing decisions
- still produce the best-possible draft structure
- mark uncertain items explicitly instead of smearing ambiguity across all issues

## Examples
- `Turn docs/plans/phase-1.md into a GitHub EPIC and child issues`
- `Convert this roadmap folder into a normalized issue set for Codex execution`
