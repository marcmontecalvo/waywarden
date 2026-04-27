---
type: architecture
title: "ADR 0006: V1/V2/V3 Roadmap"
status: Accepted
date: 2026-04-27
adr_number: "0006"
relates_to: [0001, 0002, 0009, 0011]
supersedes: null
superseded_by: null
---

# ADR 0006: V1 / V2 / V3 roadmap

## V1
Core harness plus first full profile.

### Core
- web API
- CLI entrypoint
- multi-instance support
- profile loader
- extension registry
- model router
- token accounting
- global tracer abstraction
- approvals/policy engine
- Honcho adapter
- LLM-Wiki adapter

### First full profile
- EA profile

### EA profile scope
- tasks
- inbox / scheduling primitives
- routines
- approvals
- delegation envelopes
- shared widgets and commands filtered into EA

## V2
Coding profile and richer operations.

### Add
- coding profile
- till-done / worklist loop
- adversarial review routine
- sub-agent primitive
- teams and pipelines
- repo-aware context
- TUI
- richer observability
- optional compression plugins
- backup / restore, scheduler, and workspace safety primitives

### P8 durability scope
P8 separates three related but different durability features:

1. **System backup / restore**: infrastructure durability for the Waywarden deployment itself, including Postgres data, configs, artifacts, run history, event history, workspace manifests, and any required runtime files. This answers: can Waywarden recover if the host, volume, or database is lost?
2. **Run checkpoint / resume**: execution durability for in-flight agent work, using durable run records, RT-001 manifests, RT-002 events, and checkpoints to recover or continue a run after worker loss, UI disconnect, or restart. This answers: can an interrupted run continue safely from durable state?
3. **Workspace rollback**: coding/workspace safety for reverting file, repo, or workspace changes made by an agent to a known previous point. This answers: can operator-visible work product be inspected and reverted if the agent made a bad change?

These features may interact, but they are not the same system and should not be implemented as one vague backup feature.

## V3
Home profile and deeper background systems.

### Add
- home profile
- room/device context
- HA adapters
- optional reflection / dream backlog work
- optional universal multi-runtime event bus if real need exists
