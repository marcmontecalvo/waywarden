# waywarden

Waywarden is an EA-first agent harness: a small, public, production-shaped executive assistant runtime built for long-lived memory, curated knowledge, clean tool boundaries, and future handoff to separate Home Assistant and coding runtimes.

## Positioning

This repo is **not**:
- the HA runtime
- the coding runtime
- a general-purpose autonomous “agent OS”
- a fork of OpenClaw or Hermes

This repo **is**:
- the EA core
- a native Python app for a dedicated Ubuntu VM
- a FastAPI service with clean adapter boundaries
- a Postgres-backed system of record
- a modular harness with swappable memory, knowledge, tool, model, and channel providers

## Current stack targets

- Ubuntu 24.04.4 LTS
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
- Honcho for memory
- LLM-Wiki for curated knowledge

## Design rules

1. **EA-only substrate**
   The EA owns its own runtime. HA and coding integrate through protocols, not shared internals.

2. **Memory is not knowledge**
   Honcho handles agent memory. LLM-Wiki handles curated, inspectable knowledge.

3. **No self-editing governance**
   The EA can learn preferences and routines. It cannot rewrite its own permissions, policy, or identity.

4. **No dream system in the hot path**
   Reflection, consolidation, and summarization are background jobs only.

5. **No giant god prompt**
   Architecture lives in code, configs, contracts, and tests.

## Why this exists

Forking existing harnesses is attractive for a demo but expensive for ownership.

This repo borrows ideas from:
- HKUDS/OpenHarness: docs-first onboarding, file-based skills/plugins, and “small, inspectable harness” philosophy
- MaxGfeller/open-harness: code-first sessions, event streaming, composable agent loop ideas
- jeffrschneider/OpenHarness: capability manifests and interoperable harness API/spec thinking
- Hermes Agent: reflection and learning as a concept
- OpenClaw: plugin categories and practical channel/tool/model separation

It intentionally avoids inheriting their entire runtime assumptions.

## Getting started

### 1. Install system dependencies
- Python 3.13
- `uv`
- Postgres 17+
- Docker Engine (sidecars only)

### 2. Bootstrap
```bash
make bootstrap
cp .env.example .env
make db-up
make migrate
make dev
```

### 3. Smoke test
```bash
curl http://127.0.0.1:8000/healthz
```

## Repository map

- `docs/architecture/`: ADRs and architecture decisions
- `docs/issues/`: phased execution backlog
- `docs/prompts/`: prompts for coding agents
- `config/`: runtime/provider/skill/policy config
- `infra/`: docker sidecars and systemd units
- `src/ea/`: application code
- `tests/`: unit, integration, and contract tests

## First milestone

Deliver a real EA core with:
- web API
- CLI entrypoint
- session/message/task persistence
- skill registry
- model router
- Honcho adapter
- LLM-Wiki adapter
- Gmail/calendar/contact tool stubs
- coding handoff adapter
- HA gateway adapter
- approval engine
- backups

## Public repo note

The recommended public repo name is **Waywarden**:
- implies keeping a person on course
- works for an executive-assistant core
- is flexible enough for future expansion
- avoids collisions with existing “OpenHarness” branding

See `docs/architecture/0009-name-and-positioning.md` for naming notes.
