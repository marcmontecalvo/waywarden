---
type: spec
title: "Adversarial Review Checklist"
status: Complete
date: 2026-04-28
author: core-team
spec_number: "P7-7"
phase: profile-coding
relates_to_adrs: [0007, 0008]
depends_on: [P7-6]
owner: core-team
target_milestone: "M5-b"
tags: [adversarial-review, approval, policy, fixtures]
---

# Adversarial Review Checklist

## Purpose

Use this checklist when a dispatcher, team, pipeline, or sub-agent handback crosses
the `adversarial-review` checkpoint. The routine is deterministic and
policy-backed; this checklist is the operator-facing procedure for reviewing its
findings, updating fixture coverage, and deciding whether handback can continue.

## Required Review Passes

### Prompt Injection

- Look for instructions that try to override system, developer, policy, or
  operator guidance.
- Treat requests to reveal hidden prompts, developer messages, system messages,
  or chain-of-thought as findings.
- Verify the finding includes an evidence reference to the reviewed handback
  artifact and an approval explanation with the gate decision.

### Approval-Boundary Misuse

- Look for self-approval, auto-approval, bypass, or "without approval" language.
- Confirm the finding routes through the approval engine with
  `approval_kind=adversarial_review`.
- Do not accept a handback that claims approval was granted unless the approval
  object exists and matches the requested capability.

### Malformed Memory/Knowledge Inputs

- Check memory inputs for non-empty `id` and `content` fields.
- Check knowledge inputs for non-empty `id` and `source` fields.
- Treat missing or blank fields as malformed memory/knowledge inputs because
  they make provenance and later recall unsafe.

### Destructive Tool Misuse

- Look for destructive command tokens such as `rm -rf`, `mkfs`,
  `diskutil erase`, `format`, `git reset --hard`, or `shutdown`.
- Treat destructive tool actions such as `delete`, `destroy`, and `format` as
  critical unless an explicit policy preset permits the exact operation.
- Confirm destructive tool misuse gates to `abort` when policy resolves it to
  `forbidden`.

## Fixture Set

The CI-executable fixture set lives under `tests/fixtures/adversarial/` with one
directory per canonical mode:

- `prompt_injection/`
- `approval_boundary_misuse/`
- `malformed_memory_knowledge/`
- `destructive_tool_misuse/`
- `control/`

Each fixture is data-only JSON and is executed by
`tests/services/orchestration/test_adversarial_review.py`. The test job runs
non-integration pytest on both Linux and Windows, so fixtures must remain
platform-neutral: no shell scripts, no absolute host paths, and no OS-specific
line-ending assumptions.

## Finding Metadata Requirements

Every adversarial finding from these fixtures must include:

- a typed `finding_class`
- a severity
- evidence references
- a gate decision
- approval IDs when approval is requested
- the active policy preset
- policy decisions keyed by finding class
- rationale explaining why the checkpoint continues, branches, or aborts

The clean control fixture must produce no findings and must not create approval
requests.

## Revision Workflow

The core team owns this checklist and the fixture set.

Update it when any of these change:

- a detector keyword or class changes
- a policy preset changes adversarial-review routing
- a new handback artifact shape is introduced
- a regression or incident reveals a missed adversarial path
- an ADR or spec changes the approval or pipeline checkpoint contract

Review process:

- Update this runbook and the matching JSON fixture in the same pull request.
- Add or update tests proving the fixture produces the expected finding class
  and approval-explanation metadata.
- Run `make lint`, `make test`, and `uv run mypy src tests` before merge.
- Require review from the owner of the affected routine, policy preset, or
  pipeline contract.
