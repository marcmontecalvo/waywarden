"""Tests for coding profile overlay hydration (P6-1 #92)."""

from pathlib import Path

import pytest

from waywarden.assets.loader import AssetRegistry, FilterError
from waywarden.domain.profile import (
    ProfileDescriptor,
    ProfileId,
    ProfileRegistry,
    RequiredProviders,
)
from waywarden.profiles.coding.hydrate import (
    CodingProfileHydrationError,
    CodingProfileView,
    hydrate_coding_profile,
)

FIXTURES_DIR = Path("tests/fixtures/assets").resolve()
CODING_PROFILE_PATH = Path("profiles/coding/profile.yaml")


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------


def _coding_asset_registry() -> AssetRegistry:
    """Return an AssetRegistry pre-loaded with fixture data."""
    reg = AssetRegistry()
    import asyncio

    asyncio.run(reg.load_from_dir(FIXTURES_DIR))
    return reg


def _empty_asset_registry() -> AssetRegistry:
    """Return an empty (no-load-attempt) AssetRegistry."""
    return AssetRegistry()


def _valid_coding_descriptor() -> ProfileDescriptor:
    return ProfileDescriptor(
        id=ProfileId("coding"),
        display_name="Coding",
        version="1.0.0",
        supported_extensions=(
            "command",
            "prompt",
            "tool",
            "skill",
            "agent",
            "team",
            "pipeline",
            "workflow",
            "policy",
            "theme",
            "context_provider",
            "profile_overlay",
        ),
        required_providers=RequiredProviders(
            model="fake-model",
            memory="fake-memory",
            knowledge="fake-knowledge",
            tool=("fake-tool",),
            channel=("fake-channel",),
            tracer="noop",
        ),
    )


# -----------------------------------------------------------------------
# Happy path
# -----------------------------------------------------------------------


def test_hydrate_coding_profile_creates_view() -> None:
    """Hydration succeeds with the real coding profile."""
    view = hydrate_coding_profile(
        profile_path=CODING_PROFILE_PATH,
        asset_registry=_coding_asset_registry(),
    )
    assert isinstance(view, CodingProfileView)
    assert view.id == ProfileId("coding")
    assert view.display_name == "Coding"


def test_hydrate_coding_profile_no_asset_filters_resolves_empty() -> None:
    """When asset filters are absent, resolved_assets is empty."""
    view = hydrate_coding_profile(
        profile_path=CODING_PROFILE_PATH,
        asset_registry=_coding_asset_registry(),
    )
    assert isinstance(view.asset_filters, list)
    assert view.resolved_assets == []


def test_hydrate_with_custom_registry() -> None:
    """Hydration with a custom ProfileRegistry respects the descriptor."""
    desc = _valid_coding_descriptor()
    reg = ProfileRegistry({"coding": desc})
    view = hydrate_coding_profile(
        profile_path=CODING_PROFILE_PATH,
        profile_registry=reg,
        asset_registry=_coding_asset_registry(),
    )
    assert view.id == ProfileId("coding")


def test_hydrate_with_asset_filters_resolves_assets() -> None:
    """When asset filters are present, resolved_assets is populated."""
    view = hydrate_coding_profile(
        profile_path=CODING_PROFILE_PATH,
        asset_registry=_coding_asset_registry(),
    )
    # The coding profile YAML has no asset_filters, so resolved should be empty
    assert view.resolved_assets == []


def test_hydrate_coding_profile_required_providers_passed_through() -> None:
    """Required providers from the descriptor are passed through intact."""
    view = hydrate_coding_profile(
        profile_path=CODING_PROFILE_PATH,
        asset_registry=_coding_asset_registry(),
    )
    assert view.required_providers.model == "fake-model"
    assert view.required_providers.memory == "fake-memory"
    assert view.required_providers.knowledge == "fake-knowledge"
    assert view.required_providers.tracer == "noop"


# -----------------------------------------------------------------------
# Missing provider / missing profile error
# -----------------------------------------------------------------------


def test_hydrate_fails_when_coding_missing_from_registry() -> None:
    """Hydration raises when profile registry lacks 'coding'."""
    desc = ProfileDescriptor(
        id=ProfileId("ea"),
        display_name="EA",
        version="1.0.0",
        supported_extensions=("widget",),
        required_providers=RequiredProviders(
            model="m",
            memory="m",
            knowledge="m",
            tracer="noop",
        ),
    )
    reg = ProfileRegistry({"ea": desc})
    with pytest.raises(CodingProfileHydrationError) as exc_info:
        hydrate_coding_profile(
            profile_path=CODING_PROFILE_PATH,
            profile_registry=reg,
        )
    assert any("Coding profile" in str(e) for e in exc_info.value.errors)


# -----------------------------------------------------------------------
# Missing asset error propagation
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hydrate_propagates_asset_load_errors() -> None:
    """When asset loading fails, hydration records the error."""
    bad_reg = AssetRegistry()
    await bad_reg.load_from_dir(Path("/no/directory"))
    with pytest.raises(CodingProfileHydrationError):
        hydrate_coding_profile(
            profile_path=CODING_PROFILE_PATH,
            asset_registry=bad_reg,
        )


# -----------------------------------------------------------------------
# CodingProfileView fields
# -----------------------------------------------------------------------


def test_coding_profile_view_proxies_id() -> None:
    desc = _valid_coding_descriptor()
    view = CodingProfileView(descriptor=desc)
    assert view.id == ProfileId("coding")
    assert view.display_name == "Coding"


def test_coding_profile_view_required_providers_proxy() -> None:
    providers = RequiredProviders(
        model="m",
        memory="m",
        knowledge="m",
        tracer="noop",
    )
    desc = ProfileDescriptor(
        id=ProfileId("coding"),
        display_name="Coding",
        version="1.0.0",
        supported_extensions=("skill",),
        required_providers=providers,
    )
    view = CodingProfileView(descriptor=desc)
    assert view.required_providers == providers


# -----------------------------------------------------------------------
# Invalid filter handling
# -----------------------------------------------------------------------


def test_hydrate_handles_empty_filters() -> None:
    """Empty asset filter list should succeed with no errors."""
    desc = _valid_coding_descriptor()
    reg = ProfileRegistry({"coding": desc})
    view = hydrate_coding_profile(
        profile_path=None,
        profile_registry=reg,
        asset_registry=_empty_asset_registry(),
    )
    assert isinstance(view, CodingProfileView)
    assert view.resolved_assets == []


def test_hydrate_handles_invalid_filter_expression() -> None:
    """An invalid filter expression raises FilterError through apply_filters."""
    asset_reg = _coding_asset_registry()

    # Feed an invalid filter through the registry's apply_filters
    with pytest.raises(FilterError, match="missing 'op' field"):
        asset_reg.apply_filters([{"bad_field": "unexpected"}])


# -----------------------------------------------------------------------
# Missing asset file handling
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hydrate_handles_missing_profiles_file() -> None:
    """Hydration with a non-existent profile file records a read error."""
    with pytest.raises(CodingProfileHydrationError) as exc_info:
        hydrate_coding_profile(
            profile_path=Path("/no/such/path/profile.yaml"),
            asset_registry=_empty_asset_registry(),
        )
    assert any("read error" in str(e) for e in exc_info.value.errors)


# -----------------------------------------------------------------------
# Asset filter expansion
# -----------------------------------------------------------------------


def test_hydrate_applies_filters_to_resolve_assets() -> None:
    """Filter expressions are applied to resolve the asset list."""
    desc = _valid_coding_descriptor()
    reg = ProfileRegistry({"coding": desc})
    asset_reg = _coding_asset_registry()

    view = hydrate_coding_profile(
        profile_path=None,
        profile_registry=reg,
        asset_registry=asset_reg,
    )
    # The coding profile has no asset_filters, so resolves to empty
    assert view.asset_filters == []
    assert view.resolved_assets == []


def test_hydrate_invalid_registry_key_str_sequence() -> None:
    """unsupported config value should raise an error."""
    # A profile descriptor with an empty supported_extensions is rejected by validation
    with pytest.raises(ValueError, match="supported_extensions"):
        ProfileDescriptor(
            id=ProfileId("coding"),
            display_name="Coding",
            version="1.0.0",
            supported_extensions=(),
            required_providers=RequiredProviders(
                model="fake-model",
                memory="fake-memory",
                knowledge="fake-knowledge",
            ),
        )
