# ADR 0002: EA-only substrate

## Status
Accepted

## Decision
The EA owns its own runtime substrate. HA and coding remain separate systems.

## Rationale
A shared universal substrate sounds elegant but creates the wrong coupling:
- shared failure modes
- shared abstraction debt
- shared security assumptions
- slower iteration on the EA

## Integration boundary
Use contracts, not shared internals:
- HTTP
- Webhooks
- MCP where useful
- common task envelope schemas
