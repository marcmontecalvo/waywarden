"""Tests for policy schema — PolicyPresetDoc round-trips and domain conversion."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from waywarden.policy.loader import PolicyLoader
from waywarden.policy.schema import PolicyPresetDoc, ToolDecisionRule


class TestToolDecisionRuleSchema:
    """Unit tests for the parsed rule document model."""

    def test_minimal_rule_defaults(self) -> None:
        rule = ToolDecisionRule(tool="shell")
        assert rule.tool == "shell"
        assert rule.action is None
        assert rule.decision == "approval-required"  # default
        assert rule.reason is None

    def test_full_rule(self) -> None:
        rule = ToolDecisionRule(
            tool="http",
            action="post",
            decision="forbidden",
            reason="May trigger external state changes",
        )
        assert rule.tool == "http"
        assert rule.action == "post"
        assert rule.decision == "forbidden"
        assert rule.reason == "May trigger external state changes"

    def test_unknown_decision_raises(self) -> None:
        with pytest.raises(ValidationError):
            ToolDecisionRule(  # type: ignore[arg-type]
                tool="shell.write",
                decision="instant-kill",
            )

    def test_unknown_tool_action_allowed(self) -> None:
        """The schema does not restrict tool names — only decisions are enumerated."""
        rule = ToolDecisionRule(tool="any:vendor:special", decision="auto-allow")
        assert rule.tool == "any:vendor:special"


class TestPolicyPresetDocSchema:
    """Unit tests for the preset document model."""

    def test_preset_doc_roundtrips_yaml(self) -> None:
        """YAML-style dict roundtrips through pydantic validation."""
        raw = {
            "name": "test",
            "preset": "ask",
            "default_decision": "approval-required",
            "rules": [
                {"tool": "shell.read", "decision": "auto-allow", "reason": "Safe"},
            ],
        }
        doc = PolicyPresetDoc(**raw)
        assert doc.preset == "ask"
        assert len(doc.rules) == 1
        assert doc.rules[0].tool == "shell.read"
        assert doc.rules[0].decision == "auto-allow"
        assert doc.rules[0].reason == "Safe"

    def test_default_decision_defaults_to_approval_required(self) -> None:
        doc = PolicyPresetDoc(name="yolo", preset="yolo", rules=[])
        assert doc.default_decision == "approval-required"

    @pytest.mark.parametrize(
        "preset,default_decision",
        [
            ("yolo", "auto-allow"),
            ("ask", "approval-required"),
            ("allowlist", "forbidden"),
            ("custom", "auto-allow"),
        ],
    )
    def test_all_preset_values_acceptable(self, preset: str, default_decision: str) -> None:
        doc = PolicyPresetDoc(
            name=preset, preset=preset, rules=[], default_decision=default_decision
        )
        assert doc.preset == preset
        assert doc.default_decision == default_decision

    def test_preset_doc_to_domain_proper_tool_policy(self) -> None:
        """PolicyPresetDoc converts to domain ToolPolicy via loader."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            tmp_path.joinpath("ask.yaml").write_text(
                "name: ask\npreset: ask\ndefault_decision: approval-required\n"
                "rules:\n"
                "  - tool: shell\n"
                "    action: read\n"
                "    decision: auto-allow\n"
                "    reason: safe\n"
                "  - tool: shell\n"
                "    action: write\n"
                "    decision: forbidden\n"
                "    reason: destructive\n",
                encoding="utf-8",
            )
            loader = PolicyLoader(presets_dir=tmp_path)
            policy = loader.load("ask")

        assert policy.preset == "ask"  # type: ignore[comparison-overlap]
        assert policy.default_decision == "approval-required"
        assert len(policy.rules) == 2
        assert policy.rules[0].tool == "shell"
        assert policy.rules[0].action == "read"
        assert policy.rules[0].decision == "auto-allow"
        assert policy.rules[0].reason == "safe"
        assert policy.rules[1].tool == "shell"
        assert policy.rules[1].action == "write"
        assert policy.rules[1].decision == "forbidden"
        assert policy.rules[1].reason == "destructive"

    def test_preset_doc_invalid_decision_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PolicyPresetDoc(name="test", preset="ask", rules=[], default_decision="instant")  # type: ignore[arg-type]

    def test_preset_doc_empty_rules_is_valid(self) -> None:
        doc = PolicyPresetDoc(name="yolo", preset="yolo", rules=[])
        assert doc.rules == []

    def test_preset_doc_invalid_preset_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PolicyPresetDoc(name="magic", preset="instant", rules=[])
