---
type: spec
title: "CI / CD Configuration"
status: Complete
date: 2026-04-27
spec_number: "CI-001"
phase: harness-core
relates_to_adrs: null
tags: [ci, testing, github-actions, integration-tests]
---

# CI / CD

## Jobs

| Job | OS | What runs | Integration tests |
| --- | --- | --- | --- |
| `secret-scan` | ubuntu | Gitleaks | n/a |
| `dependency-sanity` | ubuntu + windows | `uv sync --frozen` + import check | skipped |
| `lint` | ubuntu + windows | ruff format + ruff check | skipped |
| `typecheck` | ubuntu | mypy --strict | skipped |
| `test` | ubuntu + windows | `pytest -m "not integration"` | skipped on windows |
| `integration-linux` | ubuntu | `pytest -m integration` against Postgres service | **yes** |

### Why integration tests are Linux-only

Windows runners in GitHub Actions do not support Docker services the same way
Linux runners do. The `integration-linux` job spins up a `postgres:18.3-alpine3.23`
service and runs all `@pytest.mark.integration` tests against it. That linux-only
gate is also where the real provider-path + Postgres-backed EA runtime proof runs,
including `tests/integration/ea/test_ea_e2e.py`.

On Windows the `test` job runs with `-m "not integration"` so unit tests stay
green without requiring Docker.

## Coverage

- `--cov-fail-under=80` enforces an 80 % gate on combined coverage.
- Coverage source: `src/waywarden` and `alembic`.
- Excluded: `alembic/versions/*.py` (generated migrations).

Coverage reports are uploaded as artifacts (`coverage-report-<os>`) for every
job that runs tests.

## Reproducing integration tests locally

```bash
make db-up            # start Postgres via docker-compose
make migrate          # apply Alembic migrations
make test-integration # run @pytest.mark.integration tests
make db-down          # stop Postgres (keeps data)
```

Or nuke everything and start fresh:

```bash
make db-nuke
make db-up
make migrate
make test-integration
```
