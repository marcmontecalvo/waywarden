---
type: setup
title: "Quickstart: Local Development"
status: Active
date: 2026-04-27
tags: [setup, local, quickstart]
---

# Quickstart: Local Development

This guide takes you from a fresh clone to a running Waywarden instance.

## Prerequisites

- Python 3.13.x
- [`uv`](https://github.com/astral-sh/uv) — the project package manager
- Docker (for the local Postgres sidecar)
- Git

## 1. Clone and install

```bash
git clone https://github.com/marcmontecalvo/waywarden.git
cd waywarden
make bootstrap
```

`make bootstrap` runs `uv sync --extra dev` which installs all core and dev
dependencies into a managed virtual environment.

## 2. Install git hooks

```bash
uv run pre-commit install
```

## 3. Configure environment

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

For a minimal local run (fake model, fake memory, filesystem knowledge):

```dotenv
WAYWARDEN_ENV=development
WAYWARDEN_DATABASE_URL=postgresql+psycopg://waywarden:waywarden@127.0.0.1:5432/waywarden_dev
```

Leave `WAYWARDEN_MODEL_ROUTER`, `WAYWARDEN_MEMORY_PROVIDER`, and
`WAYWARDEN_KNOWLEDGE_PROVIDER` unset — they default to the `fake` providers.

See [providers.md](providers.md) for wiring real providers.

## 4. Start Postgres

```bash
make db-up
```

This brings up the Docker Compose sidecar defined in
`infra/docker-compose.db.yaml`. It binds a Postgres 16 instance to
`127.0.0.1:5432` with the credentials from the example `.env`.

Wait a few seconds for Postgres to be ready, then continue.

## 5. Run migrations

```bash
make migrate
```

Applies all Alembic migrations in `alembic/versions/` to bring the schema
to `head`.

## 6. Start the server

```bash
make run
```

Or, for live-reload during development:

```bash
make dev
```

The server binds to `http://0.0.0.0:8000` by default. You can override
`WAYWARDEN_HOST` and `WAYWARDEN_PORT` in `.env`.

## 7. Smoke checks

```bash
# Liveness
curl -s http://localhost:8000/healthz | python3 -m json.tool

# Expected:
# {
#   "status": "ok",
#   "app": "waywarden",
#   "version": "..."
# }

# List profiles (CLI)
uv run waywarden list-profiles

# List instances (CLI)
uv run waywarden list-instances
```

The `/readyz` endpoint always returns `503` today — it is a fail-closed stub
that will be wired to real dependency checks in a later phase. Use `/healthz`
for basic liveness.

## Teardown

```bash
# Stop Postgres but keep the volume
make db-down

# Stop and delete all data (destructive)
make db-nuke
```

## Next steps

- [providers.md](providers.md) — wire Honcho, LLM-Wiki, and model providers
- [ea-instance.md](ea-instance.md) — configure and add EA instances
- [ea-operator-guide.md](../usage/ea-operator-guide.md) — what EA can do today
- [api-smoke-tests.md](../usage/api-smoke-tests.md) — API test commands
