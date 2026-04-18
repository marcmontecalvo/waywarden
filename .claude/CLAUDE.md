# Waywarden project instructions

## What this repo is
Waywarden is the harness core. It supports multiple profiles and multiple side-by-side instances on the same core runtime.

Treat the repo as:
- a Python-first FastAPI service
- a profile-driven harness
- an API-first platform with optional external dashboards/UIs
- a system that must keep clean boundaries between core, adapters, assets, and profiles

## What this repo is not
Do not steer the codebase toward:
- a giant autonomous agent OS
- a UI-coupled architecture
- a one-profile-only runtime
- a provider-locked architecture

## Architecture rules
- Keep the core small and legible.
- Keep business logic out of channel adapters.
- Keep provider-specific logic behind interfaces.
- Keep domain code free of provider types.
- Keep memory and knowledge separate.
- Keep policy explicit, preset-driven, and inspectable.
- Keep shared assets shared; profiles should enable/filter them instead of cloning them.
- Keep placeholder behavior honest. Do not present unimplemented systems as production-ready.

## Repo conventions
- Main code: `src/waywarden/`
- Tests: `tests/`
- Profiles: `profiles/`
- Shared assets: `assets/`
- Config: `config/`
- Infra helpers: `infra/`
- Architecture docs: `docs/architecture/`
- Historical backlog docs: `docs/issues/`
- Active execution tracking: GitHub Issues

## Build and test
Use the repo's existing commands:
- `make lint`
- `make format`
- `make test`
- `make run`
- `make dev`
- `make db-up`
- `make migrate`

Use `uv` and the existing Python tooling instead of inventing alternate local workflows.

## Working style
- Prefer small, surgical changes.
- Follow existing patterns unless the task requires a deliberate change.
- Update tests whenever behavior changes.
- Validate before claiming completion.
- Keep scope tight to the issue/task unless a related defect must be fixed for correctness.
- Do an adversarial self-review after implementation.

## Issue discipline
GitHub Issues are the active source of truth. Do not create new issue-tracking markdown files under `docs/issues/`.

When asked to work an epic, determine the next actionable child issue, implement it fully, adversarially review it, fix defects, then update and close the issue truthfully.

## Skills vs instructions
Keep long procedures in skills, not here. This file should stay focused on durable rules, repo facts, architecture boundaries, and repeated corrections.
