# AGENTS.md

## Purpose
This repo contains the EA runtime only.

It is not the HA runtime.
It is not the coding runtime.

Those systems integrate through contracts only.

## Hard constraints
- Native Python app on a dedicated VM
- Docker only for sidecars and infra
- Memory = Honcho
- Knowledge = LLM-Wiki behind an adapter boundary
- No self-editing policies or permissions
- No dream/reflection work in the request hot path
- No direct tool execution from channel adapters
- No provider-specific types in domain layer
- All external systems must be behind interfaces

## Priorities
1. Correct boundaries
2. Testable code
3. Operational clarity
4. Swapability
5. Minimal surprise

## Never do these
- Do not add HA runtime logic into this repo
- Do not add coding-agent internals into this repo
- Do not collapse memory and knowledge into one store
- Do not encode architecture only in prompt files
- Do not bypass approvals
- Do not introduce a message bus unless a real need is documented
- Do not make channels responsible for business logic
- Do not let background jobs modify governance files

## First milestone
Deliver an EA core with:
- web API
- CLI channel
- session/message/task persistence
- skill registry
- model router
- Honcho adapter
- LLM-Wiki adapter
- Gmail/calendar/contacts tool stubs
- coding handoff
- HA gateway handoff
- backups
