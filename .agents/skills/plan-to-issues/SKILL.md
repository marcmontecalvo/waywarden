---
name: plan-to-issues
description: Normalize planning docs into a GitHub EPIC and child issues that are deterministic for work-next-issue-in-given-epic and canonically aligned to repo ADRs and specs.
---

# plan-to-issues

Use this skill when the user provides planning docs and wants them converted into a machine-usable EPIC + child-issue structure.

## Objectives

- create or normalize an EPIC
- create or normalize child issues
- make ordering and dependencies explicit, using GitHub issue numbers
- make acceptance criteria and required tests executable by an implementation agent
- bind every issue to the authoritative ADR, spec, and repo path that governs it
- prevent drift between issue text and the canonical docs the issue implements

## Required template

Follow the templates in `assets/epic-template.md` and `assets/child-issue-template.md` verbatim. Each field exists for a reason.

Every child issue MUST include:
- a `Parent epic:` pointer on line 1
- `Canonical references` with exact ADR numbers, spec ids, and repo paths
- `Scope` stating absolute repo paths, typed-model flavor, sync vs async stance, and any AppConfig/schema change
- `Canonical model` block for any issue that touches a spec, with verbatim field names, enum values, and payload fields
- `Acceptance criteria` that are verifiable without reading the PR
- `Required tests` with exact test file paths and test markers
- `Blocking dependencies` as `#<issue-number> <phase-id>: <title>` entries, not bare phase ids
- `Configuration impact` that names every AppConfig field added or required

## Authoritative source rule

When drafting an issue, treat the ADR, spec, and repo path references as the source of truth.

- If the planning doc and the canonical source disagree, prefer the canonical source.
- If the planning doc requires a concept that does not yet exist canonically, the skill MUST either update the spec/ADR first or raise the contradiction for the user rather than invent vocabulary in an issue body.
- Do not invent event types, run states, manifest fields, enum values, or AppConfig fields. All such vocabulary must trace to a named spec section or ADR line.

## Dead-reference check

Before finalizing any issue body:

- every `#<number>` must be a real GitHub issue
- every ADR reference must match `docs/architecture/<adr-file>`
- every spec reference must match a file under `docs/specs/`
- every repo path must exist or be part of the issue's declared `Scope`
- phrases like "ordered-issues item N", "the EA fixture", "or equivalent", or "later" are forbidden unless they resolve to a concrete path or issue number

## Contradiction check

Before finalizing any issue body:

- cross-check acceptance criteria against the spec sections the issue depends on
- cross-check domain field names against the spec field matrix
- cross-check enum values against the spec enum table
- cross-check dependencies against the spec's own dependency declarations

## Readiness rule

An issue body is `ready` only if all blocking dependencies are closed AND all AppConfig/schema changes it depends on are already landed OR are explicitly scoped inside the issue itself.

If either condition fails, the issue must be labeled `blocked` until the dependency closes.

## Requirements

The resulting issue structure must be deterministic enough that `work-next-issue-in-given-epic` can identify the next actionable child issue without guessing.

## Token-discipline rule

When inspecting repo structure, searching references, checking issue dependencies, or validating acceptance criteria against specs/ADRs, prefer `rtk`-wrapped shell commands for high-volume output (for example: `git diff`, `git log`, `rg`, `find`, recursive directory listings, large file scans, and bulk issue/query output) unless raw output is required to resolve a contradiction precisely.

Keep planning runs lean:
- prefer targeted `rtk rg` / `rtk find` / `rtk git` queries over broad recursive dumps
- avoid pasting or relying on full noisy command output when a filtered result answers the question
- use raw commands only when exact uncompressed output is necessary to verify canonical wording, dependency state, or repo truth