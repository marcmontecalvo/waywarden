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
- Contributing conventions (DoD, labels, milestones, phase map): `docs/contributing.md`
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
GitHub Issues are the active source of truth. Do not re-introduce a markdown backlog. See `docs/contributing.md` for the Definition of Done, label taxonomy, milestones, and phase map.

When asked to work an epic, determine the next actionable child issue, implement it fully, adversarially review it, fix defects, then update and close the issue truthfully.

## Repo-local skill loading
Repo-local skills are authoritative for repeatable workflows.

Skill location convention:
- `.agents/skills/<skill-name>/SKILL.md`

When the user references a repo skill by name:
1. Do **not** call a global or built-in `Skill(<name>)` resolver first.
2. Open `.agents/skills/<skill-name>/SKILL.md` directly from the repo.
3. Treat that file as the authoritative workflow.
4. Then open and follow any files referenced by that skill under its `assets/` directory.
5. If the exact path was given by the user, use that exact path immediately instead of searching.
6. If only the skill name was given and the path is not obvious, run a single targeted repo search for:
   - `.agents/skills/<skill-name>/SKILL.md`
7. Do not spend multiple turns “discovering” a skill that already has an explicit repo path.

Prompting note:
- If a user gives both a skill name and a repo path, prioritize the repo path.
- Repo-local skills are preferred over any global skill registry for this repository.


## Task Shorthand
If the user says `ww-next <number-or-url>`, that is a direct instruction to:
- open `.agents/skills/work-next-issue-in-given-epic/SKILL.md`
- use it as the authoritative workflow
- treat the provided number or URL as the EPIC input
- do not attempt a global skill lookup first