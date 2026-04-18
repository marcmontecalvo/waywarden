"""M1 boot-slice integration smoke test.

Boots ``create_app()`` with the real fixture config and instance, asserts the
health response and request-id behaviour, exercises ``list-profiles`` and
``list-instances`` via the CLI entry-point against the real fixtures, and
confirms that invalid config surfaces an aggregated startup error.

Design notes:
- All paths are derived from this file's location so the tests are
  path-independent and run identically on Windows and Linux CI runners.
- ``load_app_config`` is called with explicit ``config_dir`` / ``cwd``
  arguments rather than relying on the cached ``get_app_config`` singleton,
  which keeps test runs hermetic.
- No mocking of app internals; real boot wiring is used throughout.
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stderr
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from waywarden import __version__
from waywarden.app import create_app
from waywarden.cli.main import run as cli_run
from waywarden.config import AppConfig, ConfigLoadError, load_app_config

# ---------------------------------------------------------------------------
# Shared fixture: repo root resolved relative to this test file so the suite
# is portable across OS and working-directory choices.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_CONFIG_DIR = REPO_ROOT / "config"
FIXTURE_PROFILES_DIR = REPO_ROOT / "profiles"


@pytest.fixture()
def fixture_app_settings() -> AppConfig:
    """Load AppConfig from the real repo fixture files."""
    return load_app_config(config_dir=FIXTURE_CONFIG_DIR, cwd=REPO_ROOT)


# ---------------------------------------------------------------------------
# 1. App boot + health endpoint
# ---------------------------------------------------------------------------


def test_m1_boot_healthz_returns_ok(fixture_app_settings: AppConfig) -> None:
    """create_app() with real fixture config serves /healthz → 200 ok."""
    client = TestClient(create_app(fixture_app_settings))

    response = client.get("/healthz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "waywarden"
    assert body["version"] == __version__
    # commit_sha is not exposed by default in the fixture config
    assert "commit_sha" not in body


def test_m1_boot_readyz_returns_503(fixture_app_settings: AppConfig) -> None:
    """create_app() with real fixture config serves /readyz → 503 not_ready."""
    client = TestClient(create_app(fixture_app_settings))

    response = client.get("/readyz")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["app"] == "waywarden"


# ---------------------------------------------------------------------------
# 2. Request-ID middleware
# ---------------------------------------------------------------------------


def test_m1_boot_server_generates_uuid_request_id(
    fixture_app_settings: AppConfig,
) -> None:
    """Middleware attaches a fresh UUID4 X-Request-ID when none is supplied."""
    client = TestClient(create_app(fixture_app_settings))

    response = client.get("/healthz")

    request_id = response.headers.get("X-Request-ID", "")
    assert request_id, "X-Request-ID header must be present"
    parsed = UUID(request_id)
    assert parsed.version == 4


def test_m1_boot_well_formed_client_request_id_echoed_in_logs(
    fixture_app_settings: AppConfig,
) -> None:
    """A well-formed client X-Request-ID is echoed in the log context."""
    stderr = io.StringIO()
    client_req_id = "client.req-integration-smoke"

    with redirect_stderr(stderr):
        client = TestClient(create_app(fixture_app_settings))
        response = client.get("/healthz", headers={"X-Request-ID": client_req_id})

    assert response.status_code == 200
    logs = [json.loads(line) for line in stderr.getvalue().splitlines() if line.strip()]
    started = next((lg for lg in logs if lg.get("msg") == "request.started"), None)
    assert started is not None, "request.started log entry must exist"
    assert started.get("client_request_id") == client_req_id


def test_m1_boot_malformed_client_request_id_is_ignored(
    fixture_app_settings: AppConfig,
) -> None:
    """A malformed (too-short) client X-Request-ID is silently discarded."""
    stderr = io.StringIO()

    with redirect_stderr(stderr):
        client = TestClient(create_app(fixture_app_settings))
        response = client.get("/healthz", headers={"X-Request-ID": "short"})

    assert response.status_code == 200
    logs = [json.loads(line) for line in stderr.getvalue().splitlines() if line.strip()]
    started = next((lg for lg in logs if lg.get("msg") == "request.started"), None)
    assert started is not None
    assert "client_request_id" not in started


# ---------------------------------------------------------------------------
# 3. CLI: list-profiles against the real fixture profiles
# ---------------------------------------------------------------------------


def test_m1_cli_list_profiles_enumerates_fixture_profiles(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``waywarden list-profiles`` prints the three checked-in fixture profiles."""
    monkeypatch.chdir(REPO_ROOT)

    exit_code = cli_run(["list-profiles"])

    assert exit_code == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines[0] == "id\tdisplay_name\tversion"
    ids = [line.split("\t")[0] for line in lines[1:]]
    assert ids == ["coding", "ea", "home"], f"unexpected profile ids: {ids}"


def test_m1_cli_list_profiles_output_is_tab_separated(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Each data row produced by ``list-profiles`` has exactly three tab-separated columns."""
    monkeypatch.chdir(REPO_ROOT)

    exit_code = cli_run(["list-profiles"])

    assert exit_code == 0
    lines = capsys.readouterr().out.strip().splitlines()
    for line in lines[1:]:
        parts = line.split("\t")
        assert len(parts) == 3, f"expected 3 columns, got {len(parts)}: {line!r}"


# ---------------------------------------------------------------------------
# 4. CLI: list-instances against the real fixture instances
# ---------------------------------------------------------------------------


def test_m1_cli_list_instances_enumerates_fixture_instance(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``waywarden list-instances`` prints the marc-ea fixture instance."""
    monkeypatch.chdir(REPO_ROOT)

    exit_code = cli_run(["list-instances"])

    assert exit_code == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines[0] == "id\tdisplay_name\tprofile_id\tconfig_path"
    assert len(lines) >= 2, "expected at least one instance data row"
    first_row = lines[1].split("\t")
    assert first_row[0] == "marc-ea"
    assert first_row[2] == "ea"


def test_m1_cli_list_instances_output_is_tab_separated(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Each data row produced by ``list-instances`` has exactly four tab-separated columns."""
    monkeypatch.chdir(REPO_ROOT)

    exit_code = cli_run(["list-instances"])

    assert exit_code == 0
    lines = capsys.readouterr().out.strip().splitlines()
    for line in lines[1:]:
        parts = line.split("\t")
        assert len(parts) == 4, f"expected 4 columns, got {len(parts)}: {line!r}"


# ---------------------------------------------------------------------------
# 5. Invalid config surfaces aggregated startup error
# ---------------------------------------------------------------------------


def test_m1_invalid_config_raises_config_load_error(tmp_path: Path) -> None:
    """load_app_config raises ConfigLoadError when required fields are missing."""
    bad_config_dir = tmp_path / "config"
    bad_config_dir.mkdir()
    # Deliberately omit required `host` field so validation fails.
    (bad_config_dir / "app.yaml").write_text("port: 9999\n", encoding="utf-8")

    with pytest.raises(ConfigLoadError) as exc_info:
        load_app_config(config_dir=bad_config_dir, cwd=tmp_path)

    message = str(exc_info.value)
    assert "Configuration loading failed:" in message
    assert "host" in message


def test_m1_invalid_config_aggregates_multiple_errors(tmp_path: Path) -> None:
    """load_app_config aggregates both YAML-level and field-level errors."""
    bad_config_dir = tmp_path / "config"
    bad_config_dir.mkdir()
    # Broken port field AND a sibling yaml with a parse error.
    (bad_config_dir / "app.yaml").write_text(
        "host: 127.0.0.1\nport: not-a-number\n",
        encoding="utf-8",
    )
    (bad_config_dir / "channels.yaml").write_text("channels: [broken\n", encoding="utf-8")

    with pytest.raises(ConfigLoadError) as exc_info:
        load_app_config(config_dir=bad_config_dir, cwd=tmp_path)

    message = str(exc_info.value)
    assert "Configuration loading failed:" in message
    # Both the sibling YAML error and the field error must appear.
    assert "channels.yaml" in message
    assert "YAML parse error" in message
    assert "port" in message
