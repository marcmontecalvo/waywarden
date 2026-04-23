from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from waywarden.cli.main import (
    _handle_list_instances,
    _handle_list_profiles,
    _handle_serve,
    build_parser,
    run,
)
from waywarden.config import AppConfig


@pytest.mark.parametrize(
    ("argv", "expected_handler"),
    [
        (["serve"], _handle_serve),
        (["list-profiles"], _handle_list_profiles),
        (["list-instances"], _handle_list_instances),
    ],
)
def test_build_parser_routes_each_supported_subcommand(
    argv: list[str],
    expected_handler: object,
) -> None:
    parser = build_parser()

    args = parser.parse_args(argv)

    assert args.command == argv[0]
    assert args.handler is expected_handler


def test_run_help_lists_available_subcommands(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        run(["--help"])

    assert exc_info.value.code == 0
    stdout = capsys.readouterr().out
    assert "serve" in stdout
    assert "list-profiles" in stdout
    assert "list-instances" in stdout


def test_run_list_profiles_prints_checked_in_fixtures(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(repo_root)

    exit_code = run(["list-profiles"])

    assert exit_code == 0
    stdout_lines = capsys.readouterr().out.strip().splitlines()
    assert stdout_lines == [
        "id\tdisplay_name\tversion",
        "coding\tCoding\t1.0.0",
        "ea\tExecutive Assistant\t1.0.0",
        "home\tHome\t1.0.0",
    ]


def test_run_list_instances_prints_checked_in_fixture(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(repo_root)

    exit_code = run(["list-instances"])

    assert exit_code == 0
    stdout_lines = capsys.readouterr().out.strip().splitlines()
    assert stdout_lines == [
        "id\tdisplay_name\tprofile_id\tconfig_path",
        "marc-ea\tMarc EA\tea\tinstances/marc-ea.yaml",
    ]


def test_run_serve_builds_app_and_passes_bind_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = AppConfig(host="127.0.0.1", port=9001, active_profile="ea", log_level="WARNING")
    sentinel_app = object()
    calls: dict[str, Any] = {}

    def fake_load_app_config() -> AppConfig:
        calls["settings_loaded"] = True
        return settings

    def fake_create_app(app_settings: AppConfig) -> object:
        calls["create_app"] = app_settings
        return sentinel_app

    def fake_uvicorn_run(app: object, *, host: str, port: int, log_level: str) -> None:
        calls["uvicorn_run"] = {
            "app": app,
            "host": host,
            "port": port,
            "log_level": log_level,
        }

    monkeypatch.setattr("waywarden.cli.main.load_app_config", fake_load_app_config)
    monkeypatch.setattr("waywarden.cli.main.create_app", fake_create_app)
    monkeypatch.setattr("waywarden.cli.main.uvicorn.run", fake_uvicorn_run)

    exit_code = run(["serve"])

    assert exit_code == 0
    assert calls["settings_loaded"] is True
    assert calls["create_app"] is settings
    assert calls["uvicorn_run"] == {
        "app": sentinel_app,
        "host": "127.0.0.1",
        "port": 9001,
        "log_level": "warning",
    }
