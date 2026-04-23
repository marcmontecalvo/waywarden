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
