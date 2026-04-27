# waywarden

Waywarden is a **slim, extensible agent harness** — one small core runtime and
many swappable profile packs. It supports multiple agents running side by side
on the same core, such as:

- a personal EA for Marc
- a personal EA for Lisa
- a coding agent
- a Home Assistant companion

All instances share the same harness architecture while remaining separately
configurable, observable, and controllable.

## Current state

**Phase P6 is underway.** The core harness, EA profile, and all backing
infrastructure are operational:

- FastAPI service with REST API and SSE streaming
- PostgreSQL-backed system of record (Alembic-managed schema)
- Profile loader (ea, coding, home)
- Multi-instance configuration (marc-ea ships by default)
- Task domain and state machine
- Run lifecycle with RT-002 event log
- Approval engine (yolo / ask / allowlist / custom presets)
- Model router (fake stub or Anthropic)
- Honcho memory adapter (optional)
- LLM-Wiki knowledge adapter (optional, filesystem fallback)
- OpenTelemetry-compatible tracing (noop by default)
- Token accounting per turn

## Quick start

```bash
git clone https://github.com/marcmontecalvo/waywarden.git
cd waywarden
make bootstrap
cp .env.example .env
make db-up
make migrate
make run
curl -s http://localhost:8000/healthz
```

Full setup instructions: [docs/setup/quickstart.md](docs/setup/quickstart.md)

## Operator docs

| Guide | Purpose |
|---|---|
| [Quickstart](docs/setup/quickstart.md) | Clone → running local instance |
| [Providers](docs/setup/providers.md) | Honcho, LLM-Wiki, model provider wiring |
| [EA Instance Config](docs/setup/ea-instance.md) | Configure and add EA instances |
| [EA Operator Guide](docs/usage/ea-operator-guide.md) | What EA can do, task and approval flows |
| [API Smoke Tests](docs/usage/api-smoke-tests.md) | Curl commands for every endpoint |

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

## Architecture

One **core runtime**, one **extension system**, one **profile system**, many **instances**.

A single deployment runs multiple instances simultaneously — `marc-ea`,
`lisa-ea`, `coding-main` — without code forks.

Design rules:
1. **One core, many profiles** — the core owns runtime primitives; profiles activate extensions.
2. **Multi-instance by design** — no code fork required per instance.
3. **Memory is not knowledge** — Honcho for runtime memory; LLM-Wiki for curated, inspectable knowledge.
4. **Providers are swappable** — Honcho and LLM-Wiki are starting choices, not permanent commitments.
5. **No giant god prompt** — architecture lives in code, configs, contracts, and tests.
6. **Policy is explicit** — approvals, YOLO mode, and auditing are policy presets, not hidden behavior.
7. **UI is optional** — APIs are the contract; dashboards and UIs live outside this repo.
8. **Token discipline is a feature** — the harness measures user-input, injected context, tool expansion, and response tokens.

## Stack

- Ubuntu 24.04 LTS
- Python 3.13.x
- `uv`
- FastAPI + Uvicorn
- Pydantic v2
- SQLAlchemy 2 + Alembic + psycopg
- PostgreSQL 16
- pytest + Ruff

## Dev commands

```bash
make bootstrap   # uv sync --extra dev
make db-up       # start Postgres sidecar (Docker)
make migrate     # alembic upgrade head
make run         # production uvicorn on :8000
make dev         # uvicorn with live reload
make test        # pytest with 80% coverage threshold
make lint        # ruff check + format check
make format      # ruff check --fix + format
make secret-scan # gitleaks over working tree
make db-down     # stop Postgres (keep data)
make db-nuke     # stop Postgres + delete volumes
```

## CLI

```bash
uv run waywarden serve           # start the server
uv run waywarden list-profiles   # show loaded profiles
uv run waywarden list-instances  # show loaded instances
uv run waywarden chat "..."      # submit a chat message
```

## App config

Settings are loaded into a strictly-typed `AppConfig`.

Precedence (highest to lowest):
1. Process environment variables with the `WAYWARDEN_` prefix
2. `.env` in the current working directory
3. `config/app.yaml`
4. `AppConfig` class defaults

`config/app.yaml` is required; startup fails explicitly if it is missing.

## Repository map

| Path | Purpose |
|---|---|
| `src/waywarden/` | Harness application code |
| `tests/` | Unit and integration tests |
| `profiles/` | Profile overlay definitions |
| `assets/` | Shared extensions (widgets, commands, skills, routines, etc.) |
| `config/` | Runtime, instance, and provider config |
| `infra/` | Docker Compose sidecars and systemd units |
| `alembic/` | Database migrations |
| `docs/architecture/` | ADRs and durable architecture decisions |
| `docs/setup/` | Operator setup guides |
| `docs/usage/` | Operator usage guides |
| `docs/contributing.md` | Definition of Done, labels, milestones, phase map |

Active execution tracking: [GitHub Issues](https://github.com/marcmontecalvo/waywarden/issues)

## Governance

- [SECURITY.md](SECURITY.md): Security reporting path and policies.
- [CONTRIBUTING.md](CONTRIBUTING.md): Developer workflow and quality gates.
- [LICENSE](LICENSE): Repo license.
