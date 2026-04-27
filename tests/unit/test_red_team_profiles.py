"""Adversarial red-team tests for P3-2 profile validation."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from waywarden.extensions.base import Extension
from waywarden.extensions.registry import ExtensionRegistry
from waywarden.profiles import ProfileStartupError, load_profiles
from waywarden.profiles.loader import validate_profile_startup


class _StaticExtension(Extension):
    def __init__(
        self,
        *,
        name: str,
        version: str,
        capabilities: frozenset[str],
    ) -> None:
        self.name = name
        self.version = version
        self.capabilities = capabilities

    def validate(self, config: Mapping[str, Any]) -> None:
        pass


def _register_provider(
    name: str,
    capability: str,
) -> _StaticExtension:
    return _StaticExtension(
        name=name,
        version="1.0.0",
        capabilities=frozenset({capability}),
    )


async def test_profile_validation_with_empty_registry_propagates_errors() -> None:
    """If the extension registry is empty, validate_profile_startup should
    NOT silently succeed. All required providers must be validated."""
    profiles_dir = Path(__file__).resolve().parents[2] / "profiles"

    registry = ExtensionRegistry()
    profile_reg = load_profiles(profiles_dir)

    with pytest.raises(ProfileStartupError) as exc_info:
        validate_profile_startup(profile_reg, registry)

    assert "unknown provider" in str(exc_info.value)


async def test_model_router_accepts_partial_provider_map() -> None:
    """Validation catches partial provider registration gaps.

    If validation receives only a subset of required providers, the
    missing ones must be reported — not silently ignored.
    """
    profiles_dir = Path(__file__).resolve().parents[2] / "profiles"
    profile_reg = load_profiles(profiles_dir)

    registry = ExtensionRegistry()
    # Only register partial -- missing 'knowledge', 'tool', 'channel', 'tracer'
    registry.register(_register_provider(name="anthropic", capability="model"))
    registry.register(_register_provider(name="fake-memory", capability="memory"))

    with pytest.raises(ProfileStartupError) as exc_info:
        validate_profile_startup(profile_reg, registry)

    message = str(exc_info.value)
    assert "unknown provider" in message
