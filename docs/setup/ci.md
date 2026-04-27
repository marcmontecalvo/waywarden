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
| `test` | ubuntu + windows | `pytest --no-cov -m "not integration"` | skipped |
| `integration-linux` | ubuntu | full `pytest` run against Postgres service | **yes** |

### Why integration tests are Linux-only

Windows runners in GitHub Actions do not support Docker services the same way
Linux runners do. The `integration-linux` job spins up a `postgres:18.3-alpine3.23`
service and runs the full suite there, including all `@pytest.mark.integration`
tests plus the coverage gate. That linux-only gate is where the real provider-path
and Postgres-backed runtime proof runs, including:

- `tests/integration/ea/test_ea_e2e.py`
- `tests/integration/coding/test_coding_till_done_e2e.py`

The cross-platform `test` matrix remains useful for fast compatibility signal,
but it intentionally disables coverage with `--no-cov` and runs only
`-m "not integration"`. That keeps the 80% threshold honest instead of failing
Windows and non-service Linux jobs for code that is only exercised by the
Postgres-backed integration paths.

## Coverage

- `--cov-fail-under=80` enforces an 80 % gate on combined coverage.
- Coverage source: `src/waywarden` and `alembic`.
- Excluded: `alembic/versions/*.py` (generated migrations).
- Test directories are not part of the coverage denominator.

The coverage report artifact is uploaded from `integration-linux`, the only CI
job that runs the full suite and therefore the only job where the 80% gate is
meaningful.

## Secret scanning

- CI runs Gitleaks in the `secret-scan` job.
- Local reproduction path: `make secret-scan`
- False positives are audited via [`.gitleaksignore`](../../.gitleaksignore).

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
