from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import psycopg
import pytest

from waywarden.config import DatabaseUrlMissing, load_alembic_database_url


def _write_checked_in_profile(tmp_path: Path) -> None:
    profiles_dir = tmp_path / "profiles" / "ea"
    profiles_dir.mkdir(parents=True)
    (profiles_dir / "profile.yaml").write_text(
        (
            "id: ea\n"
            "display_name: Executive Assistant\n"
            "version: 1.0.0\n"
            "required_providers:\n"
            "  model: fake-model\n"
            "  memory: fake-memory\n"
            "  knowledge: fake-knowledge\n"
            "supported_extensions:\n"
            "  - skill\n"
        ),
        encoding="utf-8",
    )


def test_env_raises_when_database_url_missing(tmp_path: Path) -> None:
    _write_checked_in_profile(tmp_path)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "app.yaml").write_text(
        "host: 127.0.0.1\nport: 8080\nactive_profile: ea\nenv: development\n",
        encoding="utf-8",
    )

    with pytest.raises(DatabaseUrlMissing):
        load_alembic_database_url(config_dir=config_dir, cwd=tmp_path)


@pytest.mark.integration
def test_alembic_current_empty_db(tmp_path: Path) -> None:
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
    ephemeral_database = f"{database_name}_alembic_current_empty"

    try:
        with psycopg.connect(admin_url, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(f'DROP DATABASE IF EXISTS "{ephemeral_database}"')
            cur.execute(f'CREATE DATABASE "{ephemeral_database}"')
    except psycopg.Error as exc:
        pytest.skip(f"Postgres unavailable: {exc}")

    try:
        ephemeral_url = parsed._replace(path=f"/{ephemeral_database}").geturl()
        env = os.environ.copy()
        env["WAYWARDEN_DATABASE_URL"] = ephemeral_url

        result = subprocess.run(
            ["uv", "run", "alembic", "current"],
            capture_output=True,
            check=False,
            cwd=Path(__file__).resolve().parents[2],
            env=env,
            text=True,
        )

        assert result.returncode == 0, result.stderr
        assert "(none)" in result.stdout
    finally:
        with psycopg.connect(admin_url, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (ephemeral_database,),
            )
            cur.execute(f'DROP DATABASE IF EXISTS "{ephemeral_database}"')
