from pathlib import Path

import pytest

from waywarden.config import ConfigLoadError, load_app_config


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
