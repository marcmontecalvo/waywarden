"""Tests for policy schema — PolicyPresetDoc round-trips and domain conversion."""

import pytest
from pydantic import ValidationError

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
        assert doc.rules == []
