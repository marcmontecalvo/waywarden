---
type: architecture
title: "ADR 0012: Pre-P2 ghost-code purge"
status: Accepted
date: 2026-04-18
author: Marc M.
adr_number: "0012"
relates_to: [0002, 0011]
supersedes: null
superseded_by: null
---

# ADR 0012: Pre-P2 ghost-code purge

Date: 2026-04-18
Status: Accepted

## Context

P0 and P1 closed on GitHub issues #1 and #2, but an adversarial audit found
heavy leftover scaffolding from the earlier EA-substrate architecture. The
scaffolding contradicted the P1 Definition of Done ("no persistence,
migrations, repositories, providers, orchestration, chat runtime, or EA
routines") and the harness rule in `CLAUDE.md` to keep placeholder behavior
honest.

Specifically the repo carried:

- a second `Settings` class (`src/waywarden/settings.py`) with EA-era fields
  (`database_url`, `honcho_*`, `llm_wiki_*`) shadowing the P1-2 `AppConfig`
- seven stub routers (`chat`, `tasks`, `approvals`, `skills`, `memory`,
  `knowledge`, `backups`) wired into the core `app.py` that returned
  `501`/`503` placeholders for systems that do not exist yet
- stub domain services (`orchestrator`, `response_planner`,
  `model_router`, `context_builder`, `dream_manager`, `backup_manager`,
  `approval_engine`, `tool_registry`, `skill`, `skill_registry`)
- stub adapters for every planned provider (`channels/*`, `tools/*`,
  `models/*`, `memory/*`, `knowledge/*`, `db/*`)
- an `alembic/` migration scaffold with a `sessions` table containing only
  an `id`
- EA profile `workers/` + `skills/builtin/*` stubs
- out-of-scope `config/*.yaml` files (`backups`, `channels`, `knowledge`,
  `memory`, `models`, `policies`, `skills`) plus a `config/models.yaml`
  that referenced invented model IDs
- a coverage `omit` list that hid 14 stub paths from the 80% gate, so the
  coverage metric was fictional
- `Makefile` targets for `db-up`, `db-down`, `migrate`, `worker`, `backup`
  that referenced deferred systems
- `infra/docker-compose.sidecars.yaml`, `infra/systemd/ea-*.service`, and
  `scripts/{backup_now,bootstrap_vm,llm_wiki_*}` that tied the deployment
  story to services Waywarden does not yet own

All of this was stale and would have misled future agents or humans into
treating unimplemented systems as real.

## Decision

Before starting P2, purge the ghost-code surface and re-earn the coverage
gate honestly against the real P1 slice only.

- Deleted the duplicate `Settings`, the stub routers, the stub domain
  services, the stub adapters, the `domain/models/*` sessions of record,
  the EA workers/skills scaffolding, the `alembic/` scaffold, and the
  out-of-scope config files listed above
- Rewrote `app.py` to register only the `health` router and stripped the
  unused `skill_registry` injection kwarg
- Rewrote the coverage `omit` list in `pyproject.toml` to contain only
  `__init__.py`; the gate now reflects real code
- Stripped the `Makefile` targets that referenced deferred systems
- Removed `sqlalchemy`, `alembic`, `psycopg[binary]`, `honcho-ai`,
  `orjson`, and `httpx` from project `dependencies` (kept `httpx` under
  `[dev]` for `fastapi.testclient`); P2+ can reintroduce them as they land
- Rebalanced `README.md` "Current stack targets" into an M1-actual list
  and a "planned for later milestones" list so the stack story stops
  promising systems that are not wired

Test count went from 72 to 60; the 12 tests that disappeared were all
exercising the placeholder routes, the skill registry, or the EA skills
factory — none of which survive this cleanup. Coverage is now 85.77% on
honest denominator.

## Consequences

- P2 persistence work must reintroduce dependencies and migrations behind
  real code + tests, not as empty scaffolds.
- Future router work should live behind profile packs, not in the core
  `app.py` router list, matching the harness boundary rule in ADR 0011.
- The `assets/*/.gitkeep` skeleton remains as an intentional placeholder
  for the planned asset system; it is inert and does not claim behavior.
- The `data/` directory stays as a runtime-artifact mount point and keeps
  its `.gitkeep` markers.

## Related

- EPIC P0 (#1), EPIC P1 (#2)
- `CLAUDE.md` harness rules ("Keep placeholder behavior honest", "Keep
  business logic out of channel adapters", "Keep provider-specific logic
  behind interfaces")
- ADR 0002 "core harness plus profile packs"
- ADR 0011 "harness boundaries and client surfaces"
