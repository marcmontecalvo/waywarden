---
type: spec
title: "Agent Workflow Supervisor for WayWarden"
status: Draft
date: 2026-04-17
spec_number: "AW-001"
phase: harness-core
relates_to_adrs: [0001, 0004, 0008]
depends_on: [0004-extension-contract, 0008-coding-agent-prompts]
owner: TBD
target_milestone: "v1-harness"
---

# Agent Workflow Supervisor for WayWarden

This document adapts the strongest idea from Pi's Chronicle/agent-workflow spec: long-running work should be supervised through explicit states instead of one sprawling session.

## Goal

Enable multi-stage work that survives session boundaries while keeping each stage cleanly scoped.

## Core pattern

### Supervisor
A non-working supervisor tracks workflow state and decides which specialist should handle the current stage.

### Worker stages
Each stage is handled by a fresh specialist context, not by reusing one long-lived persona forever.

### Snapshot handoff
When a stage completes, the system records a compact snapshot:
- changed files
- key findings
- pending tasks
- blockers
- next-state recommendation

That snapshot becomes the next stage's starting context.

## Good initial workflow types

- plan -> review-plan -> build -> review -> document
- recon -> plan -> build
- design -> red-team -> revise

## Why this matters

- Less persona leakage
- Cleaner context windows
- Better resumability
- Easier audit trail
- More deterministic transitions

## Recommended MVP

1. Workflow definition file
2. Explicit transition tool or command
3. Snapshot store
4. Status viewer
5. Minimal resume/restart support

## Avoid in v1

- overly complex branching logic
- automatic state jumps without explicit completion
- opaque hidden memory
