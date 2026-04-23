from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

from waywarden.config import ConfigLoadError, load_app_config
from waywarden.extensions.base import Extension
from waywarden.extensions.registry import ExtensionRegistry
from waywarden.profiles import ProfileStartupError, load_profiles, validate_profile_startup


class _StaticExtension(Extension):
    def validate(self, config: Mapping[str, object]) -> None:
        return None


def _write_profile(path: Path, *, model_provider: str = "fake-model") -> None:
    path.write_text(
        (
            "id: ea\n"
            "display_name: Executive Assistant\n"
            "version: 1.0.0\n"
            "required_providers:\n"
            f"  model: {model_provider}\n"
            "  memory: fake-memory\n"
            "  knowledge: fake-knowledge\n"
            "  tool:\n"
            "    - fake-tool\n"
            "  channel:\n"
            "    - fake-channel\n"
            "  tracer: noop\n"
            "supported_extensions:\n"
            "  - skill\n"
        ),
        encoding="utf-8",
    )


def _register_provider(registry: ExtensionRegistry, *, name: str, capability: str) -> None:
    registry.register(
        _StaticExtension(name=name, version="1.0.0", capabilities=frozenset({capability}))
    )


def test_unknown_provider_rejected(tmp_path: Path) -> None:
    profiles_dir = tmp_path / "profiles"
    (profiles_dir / "ea").mkdir(parents=True)
    _write_profile(profiles_dir / "ea" / "profile.yaml", model_provider="missing-model")
    profiles = load_profiles(profiles_dir)

    registry = ExtensionRegistry()
    _register_provider(registry, name="fake-memory", capability="memory")
    _register_provider(registry, name="fake-knowledge", capability="knowledge")
    _register_provider(registry, name="fake-tool", capability="tool")
    _register_provider(registry, name="fake-channel", capability="channel")
    _register_provider(registry, name="noop", capability="tracer")

    with pytest.raises(ProfileStartupError) as exc_info:
        validate_profile_startup(profiles, registry)

    message = str(exc_info.value)
    assert "unknown provider 'missing-model'" in message
    assert "required_providers.model" in message


def test_capability_mismatch_rejected(tmp_path: Path) -> None:
    profiles_dir = tmp_path / "profiles"
    (profiles_dir / "ea").mkdir(parents=True)
    _write_profile(profiles_dir / "ea" / "profile.yaml", model_provider="fake-model")
    profiles = load_profiles(profiles_dir)

    registry = ExtensionRegistry()
    _register_provider(registry, name="fake-model", capability="knowledge")
    _register_provider(registry, name="fake-memory", capability="memory")
    _register_provider(registry, name="fake-knowledge", capability="knowledge")
    _register_provider(registry, name="fake-tool", capability="tool")
    _register_provider(registry, name="fake-channel", capability="channel")
    _register_provider(registry, name="noop", capability="tracer")

    with pytest.raises(ProfileStartupError) as exc_info:
        validate_profile_startup(profiles, registry)

    message = str(exc_info.value)
    assert "provider 'fake-model' missing capabilities ['model']" in message
    assert "required_providers.model" in message


def test_single_active_profile_enforced(tmp_path: Path) -> None:
    profiles_dir = tmp_path / "profiles"
    (profiles_dir / "ea").mkdir(parents=True)
    _write_profile(profiles_dir / "ea" / "profile.yaml")

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "app.yaml").write_text(
        "host: 127.0.0.1\nport: 8080\nactive_profile: missing\nenv: development\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigLoadError) as exc_info:
        load_app_config(config_dir=config_dir, cwd=tmp_path)

    message = str(exc_info.value)
    assert "field `active_profile`" in message
    assert "does not match any checked-in profile" in message
