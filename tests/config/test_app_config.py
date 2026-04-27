from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import SecretStr, ValidationError

from waywarden.config import ConfigLoadError, load_app_config
from waywarden.config.settings import AppConfig
from waywarden.domain.manifest.tool_policy import ToolPreset


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


def test_database_url_required_in_production_raises(tmp_path: Path) -> None:
    _write_checked_in_profile(tmp_path)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "app.yaml").write_text(
        "host: 127.0.0.1\nport: 8080\nactive_profile: ea\nenv: production\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigLoadError) as exc_info:
        load_app_config(config_dir=config_dir, cwd=tmp_path)

    assert "field `database_url`" in str(exc_info.value)
    assert "non-empty string" in str(exc_info.value)


def test_database_url_accepts_dev_value(tmp_path: Path) -> None:
    _write_checked_in_profile(tmp_path)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "app.yaml").write_text(
        (
            "host: 127.0.0.1\n"
            "port: 8080\n"
            "active_profile: ea\n"
            "env: development\n"
            "database_url: postgresql+psycopg://dev:dev@127.0.0.1:5432/waywarden\n"
        ),
        encoding="utf-8",
    )

    config = load_app_config(config_dir=config_dir, cwd=tmp_path)

    assert config.database_url == "postgresql+psycopg://dev:dev@127.0.0.1:5432/waywarden"


def test_tracer_field_literal_enforced() -> None:
    cfg = AppConfig(host="localhost", port=8080, active_profile="ea")
    assert cfg.tracer == "noop"

    cfg_otel = AppConfig(
        host="localhost",
        port=8080,
        active_profile="ea",
        tracer="otel",
        tracer_endpoint="http://localhost:4317",
    )
    assert cfg_otel.tracer == "otel"

    with pytest.raises(ValidationError):
        AppConfig(
            host="localhost",
            port=8080,
            active_profile="ea",
            tracer=cast(Any, "invalid"),
        )


def test_tracer_otel_requires_endpoint() -> None:
    with pytest.raises(ValidationError, match="tracer_endpoint"):
        AppConfig(
            host="localhost",
            port=8080,
            active_profile="ea",
            tracer="otel",
            tracer_endpoint=None,
        )


def test_anthropic_key_required_when_selected() -> None:
    with pytest.raises(ValidationError, match="anthropic_api_key"):
        AppConfig(
            host="localhost",
            port=8080,
            active_profile="ea",
            model_router="anthropic",
        )


def test_model_router_defaults_to_fake() -> None:
    cfg = AppConfig(host="localhost", port=8080, active_profile="ea")

    assert cfg.model_router == "fake"
    assert cfg.model_router_default_provider == "fake"
    assert cfg.anthropic_api_key is None


def test_active_profile_required(tmp_path: Path) -> None:
    _write_checked_in_profile(tmp_path)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "app.yaml").write_text(
        "host: 127.0.0.1\nport: 8080\nenv: development\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigLoadError) as exc_info:
        load_app_config(config_dir=config_dir, cwd=tmp_path)

    assert "field `active_profile`" in str(exc_info.value)


def test_honcho_requires_endpoint_and_key() -> None:
    with pytest.raises(ValidationError, match="honcho_endpoint"):
        AppConfig(
            host="localhost",
            port=8080,
            active_profile="ea",
            memory_provider="honcho",
        )


def test_honcho_requires_both_endpoint_and_key() -> None:
    """If only one is provided, validation should still fail."""
    with pytest.raises(ValidationError, match="honcho_endpoint|honcho_api_key"):
        AppConfig(
            host="localhost",
            port=8080,
            active_profile="ea",
            memory_provider="honcho",
            honcho_endpoint="http://localhost:8000",
        )


def test_honcho_succeeds_when_both_provided() -> None:
    cfg = AppConfig(
        host="localhost",
        port=8080,
        active_profile="ea",
        memory_provider="honcho",
        honcho_endpoint="http://localhost:8000",
        honcho_api_key=SecretStr("test-key"),
    )
    assert cfg.memory_provider == "honcho"
    assert cfg.honcho_endpoint == "http://localhost:8000"


def test_memory_provider_defaults_to_fake() -> None:
    cfg = AppConfig(host="localhost", port=8080, active_profile="ea")
    assert cfg.memory_provider == "fake"


def test_knowledge_provider_defaults_to_filesystem() -> None:
    cfg = AppConfig(host="localhost", port=8080, active_profile="ea")
    assert cfg.knowledge_provider == "filesystem"


def test_llm_wiki_requires_endpoint_and_key() -> None:
    with pytest.raises(ValidationError, match="llm_wiki_endpoint"):
        AppConfig(
            host="localhost",
            port=8080,
            active_profile="ea",
            knowledge_provider="llm_wiki",
        )


def test_llm_wiki_requires_both_endpoint_and_key() -> None:
    """If only one is provided, validation should still fail."""
    with pytest.raises(ValidationError, match="llm_wiki_endpoint|llm_wiki_api_key"):
        AppConfig(
            host="localhost",
            port=8080,
            active_profile="ea",
            knowledge_provider="llm_wiki",
            llm_wiki_endpoint="http://localhost:8000",
        )


def test_llm_wiki_succeeds_when_both_provided() -> None:
    cfg = AppConfig(
        host="localhost",
        port=8080,
        active_profile="ea",
        knowledge_provider="llm_wiki",
        llm_wiki_endpoint="http://localhost:8000",
        llm_wiki_api_key=SecretStr("test-key"),
    )
    assert cfg.knowledge_provider == "llm_wiki"
    assert cfg.llm_wiki_endpoint == "http://localhost:8000"


def test_policy_preset_default_is_ask() -> None:
    cfg = AppConfig(host="localhost", port=8080, active_profile="ea")
    assert cfg.policy_preset == "ask"


@pytest.mark.parametrize("preset", ["yolo", "ask", "allowlist", "custom"])
def test_policy_preset_literal_enforced(preset: ToolPreset) -> None:
    cfg = AppConfig(host="localhost", port=8080, active_profile="ea", policy_preset=preset)
    assert cfg.policy_preset == preset


def test_policy_preset_invalid_literal_rejected() -> None:
    with pytest.raises(ValidationError):
        AppConfig(
            host="localhost",
            port=8080,
            active_profile="ea",
            policy_preset=cast(Any, "nonexistent"),
        )


def test_active_instance_required(tmp_path: Path) -> None:
    """active_instance pointing at a non-existent instance fails AppConfig validation."""
    profiles_dir = tmp_path / "profiles"
    (profiles_dir / "ea").mkdir(parents=True)
    (profiles_dir / "ea" / "profile.yaml").write_text(
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
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "app.yaml").write_text(
        "host: 127.0.0.1\nport: 8080\nactive_profile: ea\nactive_instance: nonexistent\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigLoadError) as exc_info:
        load_app_config(config_dir=config_dir, cwd=tmp_path)

    message = str(exc_info.value)
    assert "active_instance" in message
