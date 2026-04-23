"""Tests for PolicyLoader — load, unknown preset, domain conversion, overrides."""

from pathlib import Path

import pytest

from waywarden.domain.manifest.tool_policy import ToolPolicy
from waywarden.policy.loader import (
    PolicyLoader,
    PolicyLoaderError,
    UnknownPresetError,
)


class TestPolicyLoader:
    """Core loader functionality — load succeeds for valid presets."""

    def test_loader_returns_domain_tool_policy(self, tmp_path: Path) -> None:
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        (presets_dir / "ask.yaml").write_text(
            "preset: ask\ndefault_decision: approval-required\n"
            "rules:\n"
            "  - tool: shell\n"
            "    action: read\n"
            "    decision: auto-allow\n"
            "    reason: safe read\n",
            encoding="utf-8",
        )
        loader = PolicyLoader(presets_dir=presets_dir)
        policy = loader.load("ask")

        assert isinstance(policy, ToolPolicy)
        assert policy.preset == "ask"  # type: ignore[comparison-overlap]
        assert policy.default_decision == "approval-required"
        assert len(policy.rules) == 1
        assert policy.rules[0].tool == "shell"
        assert policy.rules[0].action == "read"
        assert policy.rules[0].decision == "auto-allow"
        assert policy.rules[0].reason == "safe read"

    def test_list_presets_returns_filenames(self, tmp_path: Path) -> None:
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        (presets_dir / "x.yaml").write_text("preset: x\nrules: []\n", encoding="utf-8")
        (presets_dir / "y.yaml").write_text("preset: y\nrules: []\n", encoding="utf-8")
        (presets_dir / "ignored.txt").write_text("not yaml\n", encoding="utf-8")

        loader = PolicyLoader(presets_dir=presets_dir)
        assert loader.list_presets() == ["x", "y"]

    def test_empty_presets_dir(self, tmp_path: Path) -> None:
        presets_dir = tmp_path / "empty"
        presets_dir.mkdir()
        loader = PolicyLoader(presets_dir=presets_dir)
        assert loader.list_presets() == []


class TestUnknownPreset:
    """Unknown preset raises UnknownPresetError."""

    def test_unknown_preset_raises(self, tmp_path: Path) -> None:
        presets_dir = tmp_path / "present"
        presets_dir.mkdir()
        loader = PolicyLoader(presets_dir=presets_dir)

        with pytest.raises(UnknownPresetError) as exc_info:
            loader.load("nonexistent")

        assert "nonexistent" in str(exc_info.value)


class TestOverrides:
    """Override precedence — override rules win over base preset."""

    def test_override_wins(self, tmp_path: Path) -> None:
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        (presets_dir / "base.yaml").write_text(
            "preset: ask\ndefault_decision: approval-required\n"
            "rules:\n"
            "  - tool: shell\n"
            "    action: read\n"
            "    decision: forbidden\n"
            "    reason: base says forbidden\n",
            encoding="utf-8",
        )
        loader = PolicyLoader(presets_dir=presets_dir)

        override_rules = [
            {
                "tool": "shell",
                "action": "read",
                "decision": "auto-allow",
                "reason": "override wins",
            },
        ]
        policy = loader.load("base", override={"rules": override_rules})

        assert policy.preset == "ask"  # type: ignore[comparison-overlap]
        assert len(policy.rules) == 1
        rule = policy.rules[0]
        assert rule.tool == "shell"
        assert rule.action == "read"
        assert rule.decision == "auto-allow"
        assert rule.reason == "override wins"

    def test_override_default_decision(self, tmp_path: Path) -> None:
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        (presets_dir / "base.yaml").write_text(
            "preset: ask\ndefault_decision: approval-required\nrules: []\n",
            encoding="utf-8",
        )
        loader = PolicyLoader(presets_dir=presets_dir)

        policy = loader.load("base", override={"default_decision": "forbidden"})
        assert policy.default_decision == "forbidden"


class TestMalformedYaml:
    """Malformed YAML raises PolicyLoaderError with useful message."""

    def test_malformed_yaml_error(self, tmp_path: Path) -> None:
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        (presets_dir / "bad.yaml").write_text(
            "preset: bad\ndefault: [broken\n",
            encoding="utf-8",
        )
        loader = PolicyLoader(presets_dir=presets_dir)

        with pytest.raises(PolicyLoaderError) as exc_info:
            loader.load("bad")

        assert "bad.yaml" in str(exc_info.value)


class TestNonMappingYaml:
    """YAML that resolves to a non-mapping is rejected."""

    def test_yaml_resolves_to_list(self, tmp_path: Path) -> None:
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()
        (presets_dir / "list.yaml").write_text(
            "- preset: yolo\n  rules: []\n",
            encoding="utf-8",
        )
        loader = PolicyLoader(presets_dir=presets_dir)

        with pytest.raises(PolicyLoaderError) as exc_info:
            loader.load("list")

        assert "did not resolve to a mapping" in str(exc_info.value)
