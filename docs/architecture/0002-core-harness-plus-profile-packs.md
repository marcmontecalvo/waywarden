---
type: architecture
title: "ADR 0002: Core Harness Plus Profile Packs"
status: Accepted
date: 2026-04-17
adr_number: "0002"
relates_to: [0001, 0006, 0007]
supersedes: null
superseded_by: null
---

# ADR 0002: Core harness plus profile packs

## Status
Accepted

## Decision
The old EA-only substrate idea is replaced with a **core harness + profile packs** model.

The core owns:
- session lifecycle
- event loop
- persistence
- provider interfaces
- extension loading
- policy and approvals
- tracing
- token accounting
- agent/team/pipeline/routine primitives

Profiles own:
- enabled tools
- widgets
- prompts
- routines
- teams
- pipelines
- context selection
- profile-specific defaults
- UI overlays

## Rationale
A shared core is still correct, but the earlier “EA-only substrate” framing was too narrow.

The right split is:
- one core harness
- many profiles
- many instances
- clean external integrations where needed

## Integration boundary
Use contracts, not hidden coupling:
- HTTP / APIs
- webhooks
- MCP where useful
- common task / delegation envelopes
- tracing and event export
