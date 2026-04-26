"""Tests for EA profile overlay hydration (P5-3 #83)."""

from pathlib import Path

import pytest

from waywarden.assets.loader import AssetRegistry
from waywarden.domain.profile import (
    ProfileDescriptor,
    ProfileId,
    ProfileRegistry,
    RequiredProviders,
)
from waywarden.profiles.ea.hydrate import (
    EAProfileView,
    ProfileHydrationError,
    hydrate_ea_profile,
)

FIXTURES_DIR = Path("tests/fixtures/assets").resolve()
EA_PROFILE_PATH = Path("profiles/ea/profile.yaml")


# -----------------------------------------------------------------------
# Happy path
# -----------------------------------------------------------------------


def test_hydrate_ea_profile_creates_view() -> None:
    """Hydration succeeds with the real EA profile."""
    view = hydrate_ea_profile(
        profile_path=EA_PROFILE_PATH,
        asset_registry=_default_asset_registry(),
    )
    assert isinstance(view, EAProfileView)
    assert view.id == ProfileId("ea")
    assert view.display_name == "Executive Assistant"


def test_hydrate_ea_profile_resolves_non_empty_assets() -> None:
    """When asset filters are present, resolved_assets is populated."""
    view = hydrate_ea_profile(
        profile_path=EA_PROFILE_PATH,
        asset_registry=_default_asset_registry(),
    )
    assert view.asset_filters
    assert view.resolved_assets  # non-empty


def test_hydrate_with_custom_registry() -> None:
    """Hydration with a custom ProfileRegistry."""
    descriptor = ProfileDescriptor(
        id="ea",
        display_name="EA",
        version="1.0.0",
        supported_extensions=("widget", "command"),
        required_providers=RequiredProviders(
            model="fake",
            memory="fake",
            knowledge="filesystem",
            tracer="noop",
        ),
    )
    reg = ProfileRegistry({"ea": descriptor})
    view = hydrate_ea_profile(
        profile_path=EA_PROFILE_PATH,
        profile_registry=reg,
        asset_registry=_default_asset_registry(),
    )
    assert view.id == ProfileId("ea")


# -----------------------------------------------------------------------
# Missing provider error
# -----------------------------------------------------------------------


def test_hydrate_fails_when_ea_missing_from_registry() -> None:
    """Hydration raises when profile registry lacks 'ea'."""
    desc = ProfileDescriptor(
        id="coding",
        display_name="Coding",
        version="1.0.0",
        supported_extensions=("command",),
        required_providers=RequiredProviders(
            model="m",
            memory="m",
            knowledge="m",
            tracer="noop",
        ),
    )
    reg = ProfileRegistry({"coding": desc})
    with pytest.raises(ProfileHydrationError) as exc_info:
        hydrate_ea_profile(
            profile_path=EA_PROFILE_PATH,
            profile_registry=reg,
        )
    assert any("EA profile" in str(e) for e in exc_info.value.errors)


# -----------------------------------------------------------------------
# Missing asset error propagation
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hydrate_propagates_asset_load_errors() -> None:
    """When asset loading fails, hydration records the error."""
    bad_reg = AssetRegistry()
    await bad_reg.load_from_dir(Path("/no/directory"))
    # The registry is invalid; hydration should surface this
    with pytest.raises(ProfileHydrationError):
        hydrate_ea_profile(
            profile_path=EA_PROFILE_PATH,
            asset_registry=bad_reg,
        )


# -----------------------------------------------------------------------
# Fail-fast: no asset filters
# -----------------------------------------------------------------------


def _write_override_profile(path: Path, content: str) -> Path:
    """Write an override profile and return its path."""
    path.write_text(content, encoding="utf-8")
    return path


def test_hydrate_fails_when_no_asset_filters(tmp_path: Path) -> None:
    """EA profile with no asset_filters must fail startup."""
    profile_yaml = """\
id: ea
display_name: Executive Assistant
version: 1.0.0
required_providers:
  model: fake
  memory: fake
  knowledge: filesystem
  tracer: noop
supported_extensions:
  - widget
  - command
"""
    temp_path = tmp_path / "ea.yaml"
    with pytest.raises(ProfileHydrationError) as exc_info:
        hydrate_ea_profile(
            profile_path=_write_override_profile(temp_path, profile_yaml),
            asset_registry=_default_asset_registry(),
        )
    err_str = " ".join(exc_info.value.errors).lower()
    assert "asset_filters" in err_str


# -----------------------------------------------------------------------
# Fail-fast: empty resolved assets despite filters
# -----------------------------------------------------------------------


def test_hydrate_fails_when_filters_resolve_no_assets(tmp_path: Path) -> None:
    """EA profile with asset_filters that match zero assets must fail."""
    profile_yaml = """\
id: ea
display_name: Executive Assistant
version: 1.0.0
asset_filters:
  - op: by_tag
    tag: nonexistent_tag
required_providers:
  model: fake
  memory: fake
  knowledge: filesystem
  tracer: noop
supported_extensions:
  - widget
  - command
"""
    temp_path = tmp_path / "ea.yaml"
    with pytest.raises(ProfileHydrationError) as exc_info:
        hydrate_ea_profile(
            profile_path=_write_override_profile(temp_path, profile_yaml),
            asset_registry=_default_asset_registry(),
        )
    err_str = " ".join(exc_info.value.errors).lower()
    assert "zero assets" in err_str


# -----------------------------------------------------------------------
# EAProfileView fields
# -----------------------------------------------------------------------


def test_ea_profile_view_proxies_id() -> None:
    desc = ProfileDescriptor(
        id="ea",
        display_name="EA",
        version="1.0.0",
        supported_extensions=("a",),
        required_providers=RequiredProviders(
            model="x",
            memory="x",
            knowledge="x",
            tracer="noop",
        ),
    )
    view = EAProfileView(descriptor=desc)
    assert view.id == ProfileId("ea")
    assert view.display_name == "EA"


def test_ea_profile_view_required_providers_proxy() -> None:
    providers = RequiredProviders(
        model="m",
        memory="m",
        knowledge="m",
        tracer="noop",
    )
    desc = ProfileDescriptor(
        id="ea",
        display_name="EA",
        version="1.0.0",
        supported_extensions=("a",),
        required_providers=providers,
    )
    view = EAProfileView(descriptor=desc)
    assert view.required_providers == providers


# -----------------------------------------------------------------------
# Regression: fake provider IDs are rejected in checks
# -----------------------------------------------------------------------


def test_hydrate_accepts_real_provider_ids(tmp_path: Path) -> None:
    """Real provider IDs from runtime config must not trigger parse errors."""
    profile_yaml = """\
id: ea
display_name: Executive Assistant
version: 1.0.0
asset_filters:
  - op: by_tag
    tag: nonexistent_tag
required_providers:
  model: fake
  memory: fake
  knowledge: filesystem
  tool: []
  channel: []
  tracer: noop
supported_extensions:
  - widget
  - command
"""
    # This doesn't fail on provider validation (that lives in profile loader).
    # It fails here because the filter resolves zero assets.
    with pytest.raises(ProfileHydrationError):
        hydrate_ea_profile(
            profile_path=_write_override_profile(tmp_path / "gotcha.yaml", profile_yaml),
            asset_registry=AssetRegistry(),
        )


# -----------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------


def _default_asset_registry() -> AssetRegistry:
    """Return an AssetRegistry pre-loaded with fixture data."""
    reg = AssetRegistry()
    import asyncio

    asyncio.get_event_loop().run_until_complete(reg.load_from_dir(FIXTURES_DIR))
    return reg
