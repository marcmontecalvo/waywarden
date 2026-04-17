---
type: spec
title: "Run Event Protocol"
status: Draft
date: 2026-04-17
spec_number: "RT-002"
phase: harness-core
relates_to_adrs: [0011]
depends_on: [0011-harness-boundaries-and-client-surfaces, RT-001]
owner: TBD
target_milestone: "v1-harness"
---

# Run Event Protocol

Define the server-side run state and append-only event surface shared across CLI, web, and future client surfaces.

## Scope

- Define run lifecycle events for creation, planning, execution, approval waits, resumptions, artifact creation, and completion
- Define reconnect semantics so clients can resume from durable server-side history after disconnect
- Define event and artifact references exposed to client surfaces without making any client the source of truth
- Define how long-running and scheduled work resumes against existing run state

## Dependencies

- ADR `0011` for protocol-first harness and client/runtime separation
- `docs/specs/runtime/workspace-manifest.md`
- Orchestration and background scheduler services

## TODO: fill from research note

- Incorporate the multi-surface and reconnectable-client signals from `docs/research/openai-codex-desktop-2026-04.md`
- Incorporate the durable execution and resumability signals from `docs/research/openai-agents-sdk-2026-04-15.md`
