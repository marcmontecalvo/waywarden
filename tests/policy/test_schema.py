"""Tests for the policy schema (Pydantic v2 models)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from waywarden.policy.schema import PolicyPresetDoc, ToolDecisionRule

REQUESTED_PRESETS = ("yolo", "ask", "allowlist", "custom")
REQUESTED_DECISIONS = ("auto-allow", "approval-required", "forbidden")


class TestToolDecisionRuleSchema:
    """ToolDecisionRule schema validation."""

    def test_minimal_rule(self) -> None:
        rule = ToolDecisionRule(tool="shell.read")
        assert rule.tool == "shell.read"
        assert rule.action is None
        assert rule.decision == "approval-required"
        assert rule.reason is None

    def test_full_rule(self) -> None:
        rule = ToolDecisionRule(
            tool="shell.write",
            action="write",
            decision="approval-required",
            reason="May affect project state",
        )
        assert rule.tool == "shell.write"
        assert rule.action == "write"
        assert rule.decision == "approval-required"
        assert rule.reason == "May affect project state"

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
    """PolicyPresetDoc schema validation."""

    def test_minimal_preset_doc(self) -> None:
        doc = PolicyPresetDoc(name="test", preset="ask", rules=[])
        assert doc.name == "test"
        assert doc.preset == "ask"
        assert doc.default_decision == "approval-required"
        assert doc.rules == []

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
        # Roundtrip: serialise and re-parse
        out = doc.model_dump()
        assert out["preset"] == "ask"
        assert out["rules"][0]["tool"] == "shell.read"

    def test_known_presets(self) -> None:
        for preset in REQUESTED_PRESETS:
            doc = PolicyPresetDoc(name=preset, preset=preset, rules=[])
            assert doc.preset == preset

    def test_unknown_preset_raises(self) -> None:
        with pytest.raises(ValidationError):
            PolicyPresetDoc(name="magic", preset="instant", rules=[])  # type: ignore[arg-type]

    def test_default_decision_values(self) -> None:
        for decision in REQUESTED_DECISIONS:
            doc = PolicyPresetDoc(name="x", preset="ask", rules=[], default_decision=decision)
            assert doc.default_decision == decision

    def test_empty_rules_is_valid(self) -> None:
        doc = PolicyPresetDoc(name="min", preset="yolo", rules=[])
        assert doc.rules == []
