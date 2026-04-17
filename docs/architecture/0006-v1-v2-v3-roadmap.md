---
type: architecture
title: "ADR 0006: V1/V2/V3 Roadmap"
status: Accepted
date: 2026-04-17
adr_number: "0006"
relates_to: [0001, 0002, 0009]
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

## V3
Home profile and deeper background systems.

### Add
- home profile
- room/device context
- HA adapters
- optional reflection / dream backlog work
- optional universal multi-runtime event bus if real need exists
