---
type: spec
title: "Workspace Manifest Model"
status: Draft
date: 2026-04-17
spec_number: "RT-001"
phase: harness-core
relates_to_adrs: [0011]
depends_on: [0011-harness-boundaries-and-client-surfaces]
owner: TBD
target_milestone: "v1-harness"
---

# Workspace Manifest Model

Define the shaped execution workspace declared by the harness before any worker or delegated task starts.

## Scope

- Define manifest fields for `inputs`, `writable_paths`, `outputs`, `network_policy`, `tool_policy`, `secret_scope`, and `snapshot_policy`
- Define which manifest fields are harness-owned versus worker-consumed
- Define validation rules so manifests stay provider-neutral and profile-aware
- Define how manifests are attached to runs, delegated tasks, and isolated sub-work

## Dependencies

- ADR `0011` for control-plane, worker, and client-surface boundaries
- Domain models for runs, checkpoints, and artifacts
- Policy presets from ADR `0005`

## TODO: fill from research note

- Incorporate the concrete manifest signals captured in `docs/research/openai-agents-sdk-2026-04-15.md`
- Align field ownership with the existing WayWarden domain model and config approach
