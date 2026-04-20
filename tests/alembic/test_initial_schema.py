"""Integration tests for the initial Alembic migration.

All tests create an ephemeral Postgres database, run ``alembic upgrade head``,
verify the schema, then tear the database down.
"""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import psycopg
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_TABLES = frozenset(
    [
        "sessions",
        "tasks",
        "messages",
        "runs",
        "run_events",
        "approvals",
        "workspace_manifests",
        "checkpoints",
        "token_usage",
    ]
)


def _ephemeral_db() -> tuple[str, str, str]:
    """Return (ephemeral_url, db_name, admin_url) or skip the test.

    Uses ``WAYWARDEN_DATABASE_URL`` as the admin connection (pointing to any
    database) to create and drop a temporary database for the test.
    """
    if platform.system() != "Linux":
        pytest.skip("integration test is Linux-only")

    base_url = os.environ.get("WAYWARDEN_DATABASE_URL", "").strip()
    if not base_url:
        pytest.skip("WAYWARDEN_DATABASE_URL is not set")

    parsed = urlparse(base_url)
    database_name = parsed.path.lstrip("/")
    if not database_name:
        pytest.skip("WAYWARDEN_DATABASE_URL must include a database name")

    admin_url = parsed._replace(path="/postgres").geturl()
    ephemeral_database = f"{database_name}_initial_schema"

    try:
        with psycopg.connect(admin_url, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(f'DROP DATABASE IF EXISTS "{ephemeral_database}"')
            cur.execute(f'CREATE DATABASE "{ephemeral_database}"')
    except psycopg.Error as exc:
        pytest.skip(f"Postgres unavailable: {exc}")

    ephemeral_url = parsed._replace(path=f"/{ephemeral_database}").geturl()
    return ephemeral_url, ephemeral_database, admin_url


def _run_alembic(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Run an alembic command and return the result."""
    return subprocess.run(
        ["uv", "run", "alembic"] + args,
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
        env=env,
        text=True,
    )


@pytest.mark.integration
def test_upgrade_creates_all_tables() -> None:
    """Upgrade creates every table from the P2-7 metadata."""
    ephemeral_url, ephemeral_database, admin_url = _ephemeral_db()

    try:
        env = os.environ.copy()
        env["WAYWARDEN_DATABASE_URL"] = ephemeral_url

        result = _run_alembic(["upgrade", "head"], env)
        assert result.returncode == 0, result.stderr

        with psycopg.connect(admin_url, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name"
            )
            existing = {row[0] for row in cur.fetchall()}

        assert existing == EXPECTED_TABLES, f"Expected {EXPECTED_TABLES}, got {existing}"
    finally:
        with psycopg.connect(admin_url, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (ephemeral_database,),
            )
            cur.execute(f'DROP DATABASE IF EXISTS "{ephemeral_database}"')


@pytest.mark.integration
def test_downgrade_drops_all_tables() -> None:
    """Downgrade drops all tables in reverse-dependency order."""
    ephemeral_url, ephemeral_database, admin_url = _ephemeral_db()

    try:
        env = os.environ.copy()
        env["WAYWARDEN_DATABASE_URL"] = ephemeral_url

        # Upgrade first
        result = _run_alembic(["upgrade", "head"], env)
        assert result.returncode == 0, result.stderr

        # Downgrade
        result = _run_alembic(["downgrade", "base"], env)
        assert result.returncode == 0, result.stderr

        with psycopg.connect(admin_url, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name"
            )
            existing = {row[0] for row in cur.fetchall()}

        assert existing == set(), f"Expected no tables, got {existing}"
    finally:
        with psycopg.connect(admin_url, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (ephemeral_database,),
            )
            cur.execute(f'DROP DATABASE IF EXISTS "{ephemeral_database}"')


@pytest.mark.integration
def test_autogenerate_is_empty_after_upgrade() -> None:
    """Running ``alembic revision --autogenerate`` after upgrade emits no ops."""
    ephemeral_url, ephemeral_database, admin_url = _ephemeral_db()

    try:
        env = os.environ.copy()
        env["WAYWARDEN_DATABASE_URL"] = ephemeral_url

        # Upgrade first
        result = _run_alembic(["upgrade", "head"], env)
        assert result.returncode == 0, result.stderr

        # Generate a new migration — should produce no ops
        result = _run_alembic(
            ["revision", "--autogenerate", "-m", "noop"],
            env,
        )
        assert result.returncode == 0, result.stderr
        # Autogenerate prints "Skipping inline nullable" warnings and
        # "No changes detected" when there is no drift.
        assert "No changes detected" in result.stdout, (
            f"Expected 'No changes detected', got: {result.stdout}"
        )
    finally:
        with psycopg.connect(admin_url, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (ephemeral_database,),
            )
            cur.execute(f'DROP DATABASE IF EXISTS "{ephemeral_database}"')


@pytest.mark.integration
def test_run_event_check_present_in_db() -> None:
    """CHECK constraints on run_events.type and runs.state exist in the schema."""
    ephemeral_url, ephemeral_database, admin_url = _ephemeral_db()

    try:
        env = os.environ.copy()
        env["WAYWARDEN_DATABASE_URL"] = ephemeral_url

        result = _run_alembic(["upgrade", "head"], env)
        assert result.returncode == 0, result.stderr

        with psycopg.connect(admin_url, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT conname, pg_get_constraintdef(oid) "
                "FROM pg_constraint "
                "WHERE conrelid = 'run_events'::regclass AND contype = 'c' "
                "ORDER BY conname"
            )
            run_event_checks: dict[str, str] = dict(cur.fetchall())

            cur.execute(
                "SELECT conname, pg_get_constraintdef(oid) "
                "FROM pg_constraint "
                "WHERE conrelid = 'runs'::regclass AND contype = 'c' "
                "ORDER BY conname"
            )
            run_checks: dict[str, str] = dict(cur.fetchall())

        assert "ck_run_events_type" in run_event_checks, (
            f"Missing ck_run_events_type. Found: {run_event_checks}"
        )
        assert "ck_run_events_seq_positive" in run_event_checks, (
            f"Missing ck_run_events_seq_positive. Found: {run_event_checks}"
        )
        assert "ck_runs_state" in run_checks, f"Missing ck_runs_state. Found: {run_checks}"
        assert "ck_runs_policy_preset" in run_checks, (
            f"Missing ck_runs_policy_preset. Found: {run_checks}"
        )
    finally:
        with psycopg.connect(admin_url, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (ephemeral_database,),
            )
            cur.execute(f'DROP DATABASE IF EXISTS "{ephemeral_database}"')
