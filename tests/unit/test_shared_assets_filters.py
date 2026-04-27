"""Tests for shared widgets + commands filtered into EA (P5-8 #88).

Proves the share-don't-clone contract from P5-2: one canonical set
of assets filtered into profiles by tag-based asset filters.
"""

from pathlib import Path

import pytest

from waywarden.assets.loader import AssetRegistry

FIXTURES_DIR = Path("assets").resolve()


# -----------------------------------------------------------------------
# Shared widgets + commands exist
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_3_widgets_exist_as_assets() -> None:
    """At least 3 widgets are seeded under assets/widgets/."""
    reg = AssetRegistry()
    await reg.load_from_dir(FIXTURES_DIR / "widgets")
    widgets = reg.get_by_kind("widget")
    assert len(widgets) >= 3


@pytest.mark.asyncio
async def test_3_commands_exist_as_assets() -> None:
    """At least 3 commands are seeded under assets/commands/."""
    reg = AssetRegistry()
    await reg.load_from_dir(FIXTURES_DIR / "commands")
    commands = reg.get_by_kind("command")
    assert len(commands) >= 3


# -----------------------------------------------------------------------
# EA filter includes EA-relevant assets
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ea_filter_includes_ea_items() -> None:
    """EA filter with include tag ea selects EA assets."""
    reg = AssetRegistry()
    await reg.load_from_dir(FIXTURES_DIR)
    filtered = reg.apply_filters([{"op": "include", "tags": ["ea"]}])
    for a in filtered:
        assert "ea" in a.tags


@pytest.mark.asyncio
async def test_ea_filter_excludes_non_ea_items() -> None:
    """EA filter with include tag ea excludes non-EA assets."""
    reg = AssetRegistry()
    await reg.load_from_dir(FIXTURES_DIR)
    filtered = reg.apply_filters([{"op": "include", "tags": ["ea"]}])
    complete = list(reg.all_assets())
    included_ids = {a.id for a in filtered}
    # At least one excluded asset should not have "ea" tag
    for asset in complete:
        if asset.id not in included_ids:
            assert "ea" not in asset.tags


# -----------------------------------------------------------------------
# Non-EA filter excludes EA assets
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_ea_filter_excludes_ea_assets() -> None:
    """A non-EA filter with exclude tag ea removes EA assets."""
    reg = AssetRegistry()
    await reg.load_from_dir(FIXTURES_DIR)
    filtered = reg.apply_filters([{"op": "exclude", "tags": ["ea"]}])
    for a in filtered:
        assert "ea" not in a.tags


# -----------------------------------------------------------------------
# Asset filters respect tag groupings
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_home_tag_asset_exists() -> None:
    """Assets tagged with 'home' should be loadable."""
    reg = AssetRegistry()
    await reg.load_from_dir(FIXTURES_DIR)
    home = reg.apply_filters([{"op": "include", "tags": ["home"]}])
    # day-planner-widget should be included
    assert any(a.id == "day-planner-widget" for a in home)


@pytest.mark.asyncio
async def test_system_tag_asset_exists() -> None:
    """Assets tagged with 'system' should be loadable."""
    reg = AssetRegistry()
    await reg.load_from_dir(FIXTURES_DIR)
    system = reg.apply_filters([{"op": "include", "tags": ["system"]}])
    assert any(a.id == "system-info-widget" for a in system)


@pytest.mark.asyncio
async def test_universal_tag_asset_exists() -> None:
    """Assets tagged with 'universal' should be loadable."""
    reg = AssetRegistry()
    await reg.load_from_dir(FIXTURES_DIR)
    universal = reg.apply_filters([{"op": "include", "tags": ["universal"]}])
    assert any(a.id == "quick-note" for a in universal)


@pytest.mark.asyncio
async def test_coding_tag_asset_exists() -> None:
    """Assets tagged with 'coding' should be loadable."""
    reg = AssetRegistry()
    await reg.load_from_dir(FIXTURES_DIR)
    coding = reg.apply_filters([{"op": "include", "tags": ["coding"]}])
    assert any(a.id == "task-flow-widget" for a in coding)


# -----------------------------------------------------------------------
# Cross-profile filter inclusion/exclusion
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_profile_two_widgets_different_tags() -> None:
    """Two widgets with different tags prove the share-don't-clone model."""
    reg = AssetRegistry()
    await reg.load_from_dir(FIXTURES_DIR / "widgets")
    excluded = reg.apply_filters([{"op": "exclude", "tags": ["ea"]}])
    # Excluded by ea tag: coding and home widgets
    elem_ids = {a.id for a in excluded}
    assert "task-flow-widget" in elem_ids
    assert "day-planner-widget" in elem_ids
    assert "dashboard-widget" not in elem_ids
