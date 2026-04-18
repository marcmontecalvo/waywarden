# Waywarden repo guidance

## Purpose
Waywarden is the core harness. It is not a one-off EA app, not a coding-only runtime, not a Home Assistant-only runtime, and not a giant autonomous agent OS.

The repo should stay:
- Python-first
- API-first
- profile-driven
- multi-instance capable
- adapter-boundary clean
- testable

## Architecture guardrails
- Keep the harness core small.
- Put provider-specific behavior behind interfaces.
- Do not leak provider types into the domain layer.
- Do not let channel adapters own business logic.
- Do not collapse memory and knowledge into one subsystem.
- Do not hardwire the runtime to a specific UI.
- Prefer shared root-level assets plus profile filtering over duplicated profile-specific copies.
- Keep policy explicit and preset-driven.
- Keep token discipline visible in code, config, contracts, and tests.

## Profile direction
The same core should support at least these profiles:
- `ea`
- `coding`
- `home`

The same deployment should support multiple named instances side by side, for example:
- `marc-ea`
- `lisa-ea`
- `coding-main`
- `ha-main`

## Repo map
- `src/waywarden/` — core application code
- `tests/` — unit, integration, and contract tests
- `profiles/` — profile descriptors and overlays
- `assets/` — shared tools, prompts, commands, routines, teams, policies, widgets, themes, and related assets
- `config/` — typed application config and later provider/profile config
- `infra/` — sidecars and local infra support
- `docs/architecture/` — ADRs and architecture decisions
- `docs/research/` — outside references and ideas worth borrowing selectively
- `docs/issues/` — historical planning only; active execution tracking is in GitHub Issues

## Tooling and commands
- Python: `3.13`
- Package/dev runner: `uv`
- Lint: `make lint`
- Format: `make format`
- Tests: `make test`
- Local app: `make run`
- Dev server: `make dev`
- Sidecar Postgres: `make db-up`
- Migrations: `make migrate`

## Working rules
- `src/waywarden` is strictly typed. Tests are checked but lightly relaxed.
- For third-party dependencies lacking stubs (e.g. `honcho`), do not use blanket ignores. Instead, add targeted `[[tool.mypy.overrides]]` in `pyproject.toml` with `ignore_missing_imports = true` mapped only to that module.
- Use existing patterns before introducing new ones.
- Make small, surgical changes unless the task explicitly requires broader refactoring.
- Update tests with every behavioral change.
- Run the most relevant checks first, then broader validation before claiming completion.
- Do not mark work complete while tests, lint, or typing are knowingly broken in touched areas.
- Prefer typed, explicit code over clever implicit behavior.
- Keep placeholders honest: never return fake-success responses for unimplemented behavior.
- Keep issue scope tight unless a directly related defect must be fixed to make the requested work actually correct.

## GitHub workflow
- Treat GitHub Issues as the source of truth for active work.
- Do not create new markdown backlog files under `docs/issues/`.
- When working from an epic, complete the next actionable child issue in order unless issue text clearly allows parallelism.
- After implementation, adversarially review your own work, fix defects, then update the issue with notes grounded in what actually changed.
- **Always use the `gh` CLI for all GitHub operations** (reading issues, posting comments, closing issues, listing PRs, etc.). Never launch a browser or browser subagent for GitHub tasks. The `gh` CLI is authenticated and is the correct tool.

## Skills and long procedures
Use repo-local skills for repeatable workflows instead of bloating this file with long procedures. This file should stay focused on durable repo facts, hard constraints, and always-on working agreements.
