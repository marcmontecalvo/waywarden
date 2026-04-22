from pathlib import Path

import pytest
from pydantic import ValidationError

from waywarden.config import ConfigLoadError, load_app_config
from waywarden.config.settings import AppConfig


def test_database_url_required_in_production_raises(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "app.yaml").write_text(
        "host: 127.0.0.1\nport: 8080\nenv: production\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigLoadError) as exc_info:
        load_app_config(config_dir=config_dir, cwd=tmp_path)

    assert "field `database_url`" in str(exc_info.value)
    assert "non-empty string" in str(exc_info.value)


def test_database_url_accepts_dev_value(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "app.yaml").write_text(
        (
            "host: 127.0.0.1\n"
            "port: 8080\n"
            "env: development\n"
            "database_url: postgresql+psycopg://dev:dev@127.0.0.1:5432/waywarden\n"
        ),
        encoding="utf-8",
    )

    config = load_app_config(config_dir=config_dir, cwd=tmp_path)

    assert config.database_url == "postgresql+psycopg://dev:dev@127.0.0.1:5432/waywarden"


def test_tracer_field_literal_enforced() -> None:
    cfg = AppConfig(host="localhost", port=8080)
    assert cfg.tracer == "noop"

    cfg_otel = AppConfig(
        host="localhost", port=8080, tracer="otel", tracer_endpoint="http://localhost:4317"
    )
    assert cfg_otel.tracer == "otel"

    with pytest.raises(ValidationError):
        AppConfig(host="localhost", port=8080, tracer="invalid")


def test_tracer_otel_requires_endpoint() -> None:
    with pytest.raises(ValidationError, match="tracer_endpoint"):
        AppConfig(host="localhost", port=8080, tracer="otel", tracer_endpoint=None)
