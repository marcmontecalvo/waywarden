from pathlib import Path

import pytest

from waywarden.config import ConfigLoadError, load_app_config


def test_load_app_config_from_yaml(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "app.yaml").write_text(
        "host: 127.0.0.1\nport: 8080\nenv: staging\nlog_level: DEBUG\n",
        encoding="utf-8",
    )

    config = load_app_config(config_dir=config_dir, cwd=tmp_path)

    assert config.host == "127.0.0.1"
    assert config.port == 8080
    assert config.env == "staging"
    assert config.log_level == "DEBUG"
    assert config.commit_sha == ""
    assert config.expose_commit_sha is False


def test_load_app_config_reports_invalid_yaml(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "app.yaml").write_text("host: [broken\nport: 8080\n", encoding="utf-8")

    with pytest.raises(ConfigLoadError) as exc_info:
        load_app_config(config_dir=config_dir, cwd=tmp_path)

    message = str(exc_info.value)
    assert "Configuration loading failed:" in message
    assert "config/app.yaml" in message
    assert "YAML parse error" in message


def test_load_app_config_reports_missing_required_field(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "app.yaml").write_text("port: 8080\n", encoding="utf-8")

    with pytest.raises(ConfigLoadError) as exc_info:
        load_app_config(config_dir=config_dir, cwd=tmp_path)

    message = str(exc_info.value)
    assert "config/app.yaml" in message
    assert "field `host`" in message
    assert "Field required" in message


def test_load_app_config_aggregates_multiple_problems(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "app.yaml").write_text("host: 127.0.0.1\nport: not-a-number\n", encoding="utf-8")
    (config_dir / "channels.yaml").write_text("channels: [broken\n", encoding="utf-8")

    with pytest.raises(ConfigLoadError) as exc_info:
        load_app_config(config_dir=config_dir, cwd=tmp_path)

    message = str(exc_info.value)
    assert "config/channels.yaml" in message
    assert "YAML parse error" in message
    assert "config/app.yaml" in message
    assert "field `port`" in message


def test_load_app_config_precedence_env_over_dotenv_over_yaml_over_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "app.yaml").write_text(
        "host: yaml-host\nport: 8080\nenv: yaml\nlog_level: WARNING\n",
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        "WAYWARDEN_HOST=dotenv-host\nWAYWARDEN_PORT=9090\nWAYWARDEN_ENV=dotenv\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("WAYWARDEN_HOST", "env-host")
    monkeypatch.setenv("WAYWARDEN_ENV", "production")

    config = load_app_config(config_dir=config_dir, cwd=tmp_path)

    assert config.host == "env-host"
    assert config.port == 9090
    assert config.env == "production"
    assert config.log_level == "WARNING"
    assert config.commit_sha == ""
