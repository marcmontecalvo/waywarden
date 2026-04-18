# AGENTS.md

## Purpose

This repo contains the **Waywarden core harness**.

It is not:
- only an EA runtime
- only a coding runtime
- only a Home Assistant runtime
- a fused giant autonomous agent OS

It is one slim harness core with profile packs and instance overlays.

## Hard constraints
- Native Python app on a dedicated VM or similar host
- Docker only for sidecars and infra
- Memory and knowledge providers must be swappable
- Honcho and LLM-Wiki are starting providers, not permanent commitments
- No self-editing policies or permissions
- No dream/reflection work in the request hot path
- No direct tool execution from channel adapters
- No provider-specific types in the domain layer
- All external systems must be behind interfaces
- APIs are the contract; any Web UI or dashboard is optional

## Architectural priorities
1. Correct boundaries
2. Multi-instance support
3. Profile-driven behavior
4. Testable code
5. Operational clarity
6. Token discipline
7. Minimal surprise

## Supported profile direction
Waywarden should support multiple profiles using the same core:
- `ea`
- `coding`
- `home`

And multiple instances of those profiles:
- `marc-ea`
- `lisa-ea`
- `coding-main`
- `ha-main`

## Shared asset rule
Widgets, commands, prompts, teams, routines, policies, and similar assets should live once in shared root-level folders and be filtered into profiles through metadata and profile config. Do not duplicate the same asset under multiple profile folders.

## Policy rule
Policy must be explicit and preset-driven.
Support presets such as:
- `yolo`
- `ask`
- `allowlist`
- `custom`

Repo-local operator-driven development may default to `yolo`, but the harness must support stricter presets cleanly.

## Never do these
- Do not collapse memory and knowledge into one store
- Do not encode architecture only in prompt files
- Do not bypass approvals/policy just because a profile is “trusted”
- Do not make channels responsible for business logic
- Do not let background jobs modify governance files
- Do not hardwire the harness to a specific UI repo
- Do not force HA and coding to live outside the harness rather than as profiles
- Do not add an overbuilt distributed architecture
- Do not add autonomous HA mutation

## Issue tracking

Epics and issues live on **GitHub Issues**: https://github.com/marcmontecalvo/waywarden/issues.
Do not open new issues as markdown files under `docs/issues/`. The files there are historical.

## First milestone
Deliver a harness core with:
- web API
- CLI entrypoint
- multi-instance support
- profile loader
- extension registry
- model router
- Honcho adapter
- LLM-Wiki adapter
- approval engine
- token accounting
- global tracer abstraction

Then deliver the first full profile:
- `ea`
