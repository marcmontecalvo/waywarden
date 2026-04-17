# ADR 0002: Core harness plus profile packs

## Status
Superseded in spirit, retained by filename for history

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
