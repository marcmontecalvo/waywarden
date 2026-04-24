<<<<<<< HEAD
"""Tests for the policy YAML loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pytest

from waywarden.domain.manifest import ToolPolicy
from waywarden.policy.loader import PolicyLoader, PolicyLoaderError, UnknownPresetError

# Resolve the real presets dir for tests.
_BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "config" / "policy" / "presets"


def _write_ask_preset(tmp_path: Path) -> None:
    """Write a minimal ask preset to a temporary directory."""
    (tmp_path / "ask.yaml").write_text(
        (
            "name: ask\n"
            "preset: ask\n"
            "default_decision: approval-required\n"
            "rules:\n"
            "  - tool: shell.read\n"
            "    decision: auto-allow\n"
            "    reason: Safe read\n"
            "  - tool: shell.write\n"
            "    decision: approval-required\n"
            "    reason: Needs approval\n"
        ),
        encoding="utf-8",
    )


class TestLoaderLoadYes:
    """Positive loader tests."""

    def test_loader_returns_domain_tool_policy(self) -> None:
        """PolicyLoader.load returns a domain ToolPolicy (frozen dataclass)."""
        tmp_path = Path(__file__).resolve().parent / "fixtures"
        tmp_path.mkdir(exist_ok=True)

        _write_ask_preset(tmp_path)
        loader = PolicyLoader(presets_dir=tmp_path)  # type: ignore[arg-type]  — intentional below
        result = loader.load("ask")

        assert isinstance(result, ToolPolicy)
        assert result.preset == "ask"
        assert result.default_decision == "approval-required"
        assert len(result.rules) == 2

        # Cleanup
        for f in tmp_path.glob("*.yaml"):
            f.unlink()
        tmp_path.rmdir()

    def test_preset_default_decision_from_yaml(self) -> None:
        """Loader respects default_decision from the YAML file."""
        tmp_path = Path(__file__).resolve().parent / "fixtures_yolo"
        tmp_path.mkdir(exist_ok=True)
        (tmp_path / "yolo.yaml").write_text(
            "name: yolo\npreset: yolo\ndefault_decision: auto-allow\nrules: []\n",
            encoding="utf-8",
        )

        try:
            loader = PolicyLoader(presets_dir=tmp_path)  # type: ignore[arg-type]
            result = loader.load("yolo")
            assert result.preset == "yolo"
            assert result.default_decision == "auto-allow"
        finally:
            for f in tmp_path.glob("*.yaml"):
                f.unlink()
            tmp_path.rmdir()


class TestLoaderUnknownPreset:
    """Unknown preset raises UnknownPresetError."""

    def test_unknown_preset_raises(self) -> None:
        tmp_path = Path(__file__).resolve().parent / "fixtures_empty"
        tmp_path.mkdir(exist_ok=True)

        try:
            loader = PolicyLoader(presets_dir=tmp_path)  # type: ignore[arg-type]
            with pytest.raises(UnknownPresetError) as exc_info:
                loader.load("nonexistent")
            assert exc_info.value.name == "nonexistent"
        finally:
            tmp_path.rmdir()


class TestLoaderOverrides:
    """Override precedence: overrides win over base rules."""

    def test_override_wins(self) -> None:
        """When an override specifies the same tool, it replaces the base rule."""
        tmp_path = Path(__file__).resolve().parent / "fixtures_override"
        tmp_path.mkdir(exist_ok=True)
        _write_ask_preset(tmp_path)

        try:
            loader = PolicyLoader(presets_dir=tmp_path)  # type: ignore[arg-type]
            override: Mapping[str, Any] = {
                "rules": [
                    {"tool": "shell.write", "decision": "forbidden", "reason": "Never allow"},
                ],
            }
            result = loader.load("ask", override=override)

            # shell.write rule should be overridden
            write_rules = [r for r in result.rules if r.tool == "shell.write"]
            assert len(write_rules) == 1
            assert write_rules[0].decision == "forbidden"
            assert write_rules[0].reason == "Never allow"

            # shell.read should still be auto-allow (not overridden)
            read_rules = [r for r in result.rules if r.tool == "shell.read"]
            assert len(read_rules) == 1
            assert read_rules[0].decision == "auto-allow"
        finally:
            for f in tmp_path.glob("*.yaml"):
                f.unlink()
            tmp_path.rmdir()

    def test_override_adds_new_rule(self) -> None:
        """Override with a tool not in the base adds it."""
        tmp_path = Path(__file__).resolve().parent / "fixtures_add"
        tmp_path.mkdir(exist_ok=True)
        _write_ask_preset(tmp_path)

        try:
            loader = PolicyLoader(presets_dir=tmp_path)  # type: ignore[arg-type]
            override: Mapping[str, Any] = {
                "rules": [
                    {"tool": "http.post", "decision": "forbidden", "reason": "Block POST"},
                ],
            }
            result = loader.load("ask", override=override)

            tools = {r.tool for r in result.rules}
            assert "http.post" in tools
        finally:
            for f in tmp_path.glob("*.yaml"):
                f.unlink()
            tmp_path.rmdir()


class TestLoaderMypy:
    """Verify mypy --strict runs cleanly on the loader module."""

    def test_preset_default_decision_from_yaml(self) -> None:
        """YAML-file mypy-neighbourly preset name is captured as is."""
        tmp_path = Path(__file__).resolve().parent / "fixtures_name"
        tmp_path.mkdir(exist_ok=True)
        (tmp_path / "myname.yaml").write_text(
            "name: myname\npreset: ask\ndefault_decision: approval-required\nrules: []\n",
            encoding="utf-8",
        )
        try:
            loader = PolicyLoader(presets_dir=tmp_path)  # type: ignore[arg-type]
            result = loader.load("myname")
            assert result.preset == "ask"
        finally:
            for f in tmp_path.glob("*"):
                f.unlink()
            tmp_path.rmdir()
=======
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
>>>>>>> 7c5089dabbd83f11c39650e78b76e58c185e571e
