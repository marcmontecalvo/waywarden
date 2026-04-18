---
name: plan-to-issues
description: Normalize planning docs into a GitHub EPIC and child issues that are deterministic for work-next-issue-in-given-epic.
---

# plan-to-issues

Use this skill when the user provides planning docs and wants them converted into a machine-usable EPIC + child-issue structure.

## Objectives

- create or normalize an EPIC
- create or normalize child issues
- make ordering and dependencies explicit
- make acceptance criteria and required tests executable by an implementation agent

## Requirements

Follow the templates in `assets/epic-template.md` and `assets/child-issue-template.md`.

The resulting issue structure must be deterministic enough that `work-next-issue-in-given-epic` can identify the next actionable child issue without guessing.
