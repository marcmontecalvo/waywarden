---
type: architecture
title: "ADR 0008: Coding-Agent Prompts"
status: Accepted
date: 2026-04-17
adr_number: "0008"
relates_to: [0001, 0004]
supersedes: null
superseded_by: null
---

# ADR 0008: Coding-agent prompts

See `docs/prompts/` for the actual prompts.

## Rule
Prompts do not define architecture by themselves.
They enforce and accelerate implementation of the ADRs.

## Additional rule
Reusable behavior such as:
- adversarial review
- advisor passes
- till-done loops
- workflow repetition

should prefer routines, teams, pipelines, and policy-backed execution over prompt-only tricks.
