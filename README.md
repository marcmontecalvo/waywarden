# waywarden

Waywarden is a **slim, extensible agent harness** built around one small core and many swappable profile packs.

The goal is to let you run multiple agents side by side — for example:
- a personal EA for Marc
- a personal EA for Lisa
- a coding agent
- a Home Assistant companion

All of them should share the same harness architecture while remaining separately configurable, observable, and controllable.

## Positioning

This repo is **not**:
- a fork of OpenClaw, Hermes, or Pi
- a giant autonomous agent OS
- a UI-specific product
- a single-purpose EA runtime

This repo **is**:
- the Waywarden core harness
- a native Python-first runtime for a dedicated Ubuntu VM or similar host
- a FastAPI service with clean adapter boundaries
- a Postgres-backed system of record
- a profile-driven harness with swappable memory, knowledge, tool, model, and channel providers
- an API-first platform that can power separate dashboards and UIs

## Architecture thesis

Waywarden should be:
- one **small core runtime**
- one **extension system**
- one **profile system**
- many **instances**

A single core should support profiles such as:
- `ea`
- `coding`
- `home`

A single deployment should also be able to run multiple configured instances at once, such as:
- `marc-ea`
- `lisa-ea`
- `coding-main`
- `ha-main`

## Current stack targets

- Ubuntu 24.04 LTS
- Python 3.13.x
- `uv`
- FastAPI
- Uvicorn
- Pydantic v2
- SQLAlchemy 2
- Alembic
- pytest
- Ruff
- Postgres
- Honcho as the starting memory provider
- LLM-Wiki as the starting knowledge provider
- OpenTelemetry-compatible tracing with a no-op mode when auditing is disabled

## App Config

Application bootstrap settings are loaded into a strictly typed `AppConfig`.

Precedence is highest to lowest:
- process environment variables with the `WAYWARDEN_` prefix
- `.env` in the current working directory
- `config/app.yaml`
- `AppConfig` class defaults

Loading behavior:
- `load_app_config()` reads `config/app.yaml` from the requested `config_dir`, defaulting to `./config`
- `.env` is resolved from the requested `cwd`, defaulting to the current process working directory
- `config/app.yaml` is required; if it is missing, loading fails with an explicit file-not-found style config error
- each load builds its YAML source per call, so repeated or concurrent loads do not mutate shared class state

Only `config/app.yaml` is schema-validated in this phase. Other `config/*.yaml` files are tolerated so later milestones can attach their own typed consumers without leaking provider-specific config into the core app model.

## Instance Fixtures

M1 instance fixtures live under `config/` in two parts:
- `config/instances.yaml`: manifest of instance descriptors for the deployment
- `config/instances/<instance-id>.yaml`: per-instance overlay file referenced by `config_path`

The manifest shape is:

```yaml
instances:
  - id: marc-ea
    display_name: Marc EA
    profile_id: ea
    config_path: instances/marc-ea.yaml
```

`config_path` is resolved relative to `config/`, and each referenced file is schema-checked against the current `InstanceConfig` shape:

```yaml
env: {}
overrides: {}
```

The checked-in default fixture is `marc-ea`, pinned to the real `ea` profile. Instance loading fails clearly if the manifest is malformed, an overlay file is invalid, or a referenced `profile_id` no longer exists in `profiles/`.

## CLI bootstrap

The M1 boot slice exposes three commands:
- `uv run waywarden serve`
- `uv run waywarden list-profiles`
- `uv run waywarden list-instances`

`serve` loads `AppConfig`, builds the FastAPI app through the shared app factory, and binds uvicorn to the configured `host` and `port`.

On Windows, the supported launch mode for this slice is the direct foreground command `uv run waywarden serve`. Stop it with `Ctrl+C`. Reload-oriented or alternate signal-management launch modes are intentionally out of scope for this milestone.

## Design rules

1. **One core, many profiles**
   The harness core owns the runtime primitives. Profiles decide which tools, widgets, prompts, routines, teams, policies, and context providers are active.

2. **Multi-instance by design**
   The same harness should support multiple side-by-side instances without code forks.

3. **Memory is not knowledge**
   Honcho handles runtime memory. LLM-Wiki handles curated, inspectable knowledge.

4. **Providers are swappable**
   Honcho and LLM-Wiki are starting providers, not permanent architecture commitments.

5. **No giant god prompt**
   Architecture lives in code, configs, contracts, and tests.

6. **Policy is explicit**
   Approvals, YOLO mode, allow/deny behavior, and auditing are policy presets, not hidden behavior.

7. **UI is optional**
   The Web UI and dashboards live outside this repo. APIs are the contract.

8. **Token discipline is a feature**
   The harness must measure user-input tokens, injected context tokens, tool/context expansion, and response tokens per turn.

## Extension surface

Waywarden should support shared root-level assets and extensions such as:
- widgets
- commands
- prompts
- tools
- skills
- agents
- teams
- pipelines
- routines
- policies
- themes
- context providers

Profiles should filter and enable these shared assets rather than duplicating them.

## Why this exists

Forking existing harnesses is attractive for a fast demo but expensive for ownership.

Waywarden borrows ideas from:
- OpenHarness variants for small, inspectable harness thinking
- Pi for extension stacking, widgets, teams, chains, and profile-like customization
- ZeroID for delegation envelopes, scoped authority, and tool-boundary trust
- Claude Code ecosystem ideas for routines, session management, subagents, advisor patterns, and auto-mode thinking
- OpenClaw command-center style tools for observability and operator UX

It intentionally avoids inheriting any one project’s full runtime assumptions.

## Repository map

- `docs/architecture/`: ADRs and architecture decisions
- `docs/issues/`: historical phased backlog — **active tracking is on [GitHub Issues](https://github.com/marcmontecalvo/waywarden/issues)** (see [docs/issues/README.md](docs/issues/README.md))
- `docs/prompts/`: prompts for coding agents
- `docs/research/`: external products, repos, and UX patterns worth borrowing from selectively
- `config/`: runtime/provider/profile/policy config
- `infra/`: docker sidecars and systemd units
- `src/`: application code
- `tests/`: unit, integration, and contract tests
- `assets/`: shared widgets, commands, prompts, routines, teams, policies, and other extension assets
- `profiles/`: profile overlays and selection rules

## Local development

- `make run`: starts the harness
- `make test`: runs the test suite
- `make lint` / `make format`: runs `ruff`
- `make secret-scan`: runs `gitleaks` over the working tree. To allow-list known false positives, add the relevant exception rules to `.gitleaksignore`.

### Type checking policy
- `src/waywarden/` stays under strict `mypy` enforcement. Tests retain lighter but checked typing.
- For third-party dependencies lacking stubs (e.g., `honcho`), do not use global `ignore_errors = true` or blanket ignores. Add targeted `[[tool.mypy.overrides]]` entries mapping to the specific module in `pyproject.toml` with `ignore_missing_imports = true`.

## Package layout

- `src/waywarden/`: harness package root
- `src/waywarden/todo/ea_profile/`: temporary home for EA-specific modules that still need to move behind a real profile overlay

## First milestone

Deliver a real core harness with:
- web API
- CLI entrypoint
- profile loader
- multi-instance support
- session/message/task persistence
- extension registry
- model router
- Honcho adapter
- LLM-Wiki adapter
- approval engine
- token accounting
## Package layout

- `src/waywarden/`: harness package root
- `src/waywarden/todo/ea_profile/`: temporary home for EA-specific modules that still need to move behind a real profile overlay

## First milestone

Deliver a real core harness with:
- web API
- CLI entrypoint
- profile loader
- multi-instance support
- session/message/task persistence
- extension registry
- model router
- Honcho adapter
- LLM-Wiki adapter
- approval engine
- token accounting
- global tracer abstraction

Then deliver the first full profile:
- `ea`

## Public repo note

The public repo name remains **Waywarden** because it:
- works for a core harness instead of a single agent persona
- is not tied to coding or smart home specifically
- implies guidance and staying on course
- avoids collision with existing OpenHarness naming

## Governance

- [SECURITY.md](SECURITY.md): Security reporting path and policies.
- [CONTRIBUTING.md](CONTRIBUTING.md): Developer workflow and quality gates.
- [LICENSE](LICENSE): Explicit repo license decision (pending maintainer choice).
