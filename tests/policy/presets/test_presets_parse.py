"""Parametrized test: all four presets parse cleanly."""

import pytest

from waywarden.policy.loader import PolicyLoader

PRESET_NAMES = ["yolo", "ask", "allowlist", "custom"]


@pytest.mark.parametrize("preset_name", PRESET_NAMES)
def test_all_four_presets_parse(preset_name: str) -> None:
    """Each preset file must exist under config/policy/presets/ and parse."""
    loader = PolicyLoader()
    policy = loader.load(preset_name)
    assert policy.preset == preset_name
    assert hasattr(policy, "rules")
    assert hasattr(policy, "default_decision")


def test_list_presets_includes_all_four() -> None:
    """PolicyLoader should discover all four preset files."""
    loader = PolicyLoader()
    presets = loader.list_presets()
    for name in PRESET_NAMES:
        assert name in presets, f"Preset '{name}' not discovered by loader"
