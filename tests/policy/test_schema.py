<<<<<<< HEAD
"""Tests for the policy schema (Pydantic v2 models)."""

from __future__ import annotations
=======
"""Tests for policy schema — PolicyPresetDoc round-trips and domain conversion."""
>>>>>>> 7c5089dabbd83f11c39650e78b76e58c185e571e

import pytest
from pydantic import ValidationError

<<<<<<< HEAD
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
=======
from waywarden.domain.manifest.tool_policy import ToolDecisionRule
from waywarden.policy.schema import PolicyPresetDoc, ToolDecisionRuleDoc


class TestToolDecisionRuleDoc:
    """Unit tests for the parsed rule document model."""

    def test_minimal_rule_defaults(self) -> None:
        rule = ToolDecisionRuleDoc(tool="shell")
        assert rule.tool == "shell"
        assert rule.action is None
        assert rule.decision == "approval-required"  # default
        assert rule.reason is None

    def test_full_rule(self) -> None:
        rule = ToolDecisionRuleDoc(
            tool="http",
            action="post",
            decision="forbidden",
            reason="May trigger external state changes",
        )
        assert rule.tool == "http"
        assert rule.action == "post"
        assert rule.decision == "forbidden"
        assert rule.reason == "May trigger external state changes"

    def test_rule_is_frozen(self) -> None:
        rule = ToolDecisionRuleDoc(tool="shell")
        with pytest.raises(ValidationError):
            rule.tool = "http"


class TestPolicyPresetDoc:
    """Unit tests for the preset document model."""

    def test_default_decision_defaults_to_approval_required(self) -> None:
        doc = PolicyPresetDoc(preset="yolo", rules=[])
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
        doc = PolicyPresetDoc(preset=preset, rules=[], default_decision=default_decision)
        assert doc.preset == preset  # type: ignore[comparison-overlap]
        assert doc.default_decision == default_decision

    def test_preset_doc_to_domain_proper_tool_policy(self) -> None:
        rules = [
            ToolDecisionRuleDoc(
                tool="shell",
                action="read",
                decision="auto-allow",
                reason="safe",
            ),
            ToolDecisionRuleDoc(
                tool="shell",
                action="write",
                decision="forbidden",
                reason="destructive",
            ),
        ]
        doc = PolicyPresetDoc(preset="ask", rules=rules, default_decision="approval-required")
        policy = doc.to_domain()

        assert policy.preset == "ask"  # type: ignore[comparison-overlap]
        assert policy.default_decision == "approval-required"
        assert len(policy.rules) == 2
        assert policy.rules[0] == ToolDecisionRule(
            tool="shell", action="read", decision="auto-allow", reason="safe"
        )
        assert policy.rules[1] == ToolDecisionRule(
            tool="shell", action="write", decision="forbidden", reason="destructive"
        )

    def test_preset_doc_invalid_decision_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PolicyPresetDoc(preset="bad", rules=[], default_decision="auto-allow")

    def test_preset_doc_empty_rules_is_valid(self) -> None:
        doc = PolicyPresetDoc(preset="yolo")
>>>>>>> 7c5089dabbd83f11c39650e78b76e58c185e571e
        assert doc.rules == []
