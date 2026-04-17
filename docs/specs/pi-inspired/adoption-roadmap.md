---
type: spec
title: "Adoption Roadmap for Pi-Inspired Patterns"
status: Draft
date: 2026-04-17
spec_number: "AR-001"
phase: harness-core
relates_to_adrs: [0001, 0006]
depends_on: [0006-v1-v2-v3-roadmap]
owner: TBD
target_milestone: "v1-harness"
---

# Adoption Roadmap

## Phase 1 — Immediate low-risk lift
Add the following:
- core worker agents
- teams.yaml
- framework experts
- orchestrator prompt

This is the fastest way to capture most of the value.

## Phase 2 — Safety
Implement the damage-control concept for destructive command and path guardrails.

## Phase 3 — Stateful workflow
Add a workflow supervisor for longer-running multi-stage work.

## Phase 4 — Controlled self-expansion
Explore Agent Forge concepts only after guardrails, review flow, and auditability are solid.

## Priority order

1. worker agents
2. plan-reviewer requirement for medium/large work
3. framework experts
4. orchestrator
5. damage-control
6. workflow supervisor
7. controlled forge/promotion flow
