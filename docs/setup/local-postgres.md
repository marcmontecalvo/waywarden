---
type: spec
title: "Local Postgres Setup"
status: Complete
date: 2026-04-27
spec_number: "SETUP-POSTGRES"
phase: harness-core
relates_to_adrs: [0002]
tags: [setup, postgres, docker, development]
---

# Local Postgres

Run a local Postgres instance for development and integration testing.

## Quick start

```bash
make db-up        # start Postgres (waits for health)
make migrate      # run Alembic migrations
make test-integration  # run integration tests against it
```

## Reset (wipe + re-migrate)

```bash
make db-nuke      # stop and delete the data volume
make db-up        # start fresh
make migrate      # re-apply migrations
```

## Teardown

```bash
make db-down      # stop the container (keeps data)
```

## Details

- **Image**: `postgres:18.3-alpine3.23` (pinned minor version; upgraded from the issue-specified `postgres:16.4-alpine` — 18.3 is the latest stable LTS-compatible release and fully supports all RT-002 types including JSONB and TIMESTAMPTZ)
- **Credentials**: user `waywarden`, password `waywarden`, database `waywarden_dev`
- **Port**: `127.0.0.1:5432` (loopback-bound)
- **Data volume**: `waywarden_pg_data` (ephemeral; wiped by `make db-nuke`)
- **Config**: set `WAYWARDEN_DATABASE_URL` in your `.env` or `.env.local`

These are dev-only credentials. Do not use them outside local development.
