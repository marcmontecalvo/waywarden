"""Tests for provider-neutral P8 durability handoff metadata."""

from __future__ import annotations

from typing import cast

import pytest

from waywarden.domain.durability import (
    SideEffectClassification,
    TokenBudgetTelemetry,
    ToolActionMetadata,
)


def test_side_effect_classification_serializes_stable_action_class() -> None:
    classification = SideEffectClassification(
        action_class="workspace-mutating",
        rationale="Writes a patch into the checked-out workspace.",
    )

    assert classification.as_payload() == {
        "action_class": "workspace-mutating",
        "rationale": "Writes a patch into the checked-out workspace.",
    }


@pytest.mark.parametrize(
    "action_class",
    [
        "read-only",
        "workspace-mutating",
        "DB-mutating",
        "provider-mutating",
        "external-write",
        "unknown/high-risk",
    ],
)
def test_tool_action_metadata_accepts_required_side_effect_classes(action_class: str) -> None:
    metadata = ToolActionMetadata(
        tool_id="shell",
        action="exec",
        side_effect=SideEffectClassification(
            action_class=action_class,
            rationale=f"{action_class} action",
        ),
    )

    side_effect = cast(dict[str, object], metadata.as_payload()["side_effect"])
    assert side_effect["action_class"] == action_class


def test_tool_action_metadata_preserves_approval_explanation() -> None:
    metadata = ToolActionMetadata(
        tool_id="shell",
        action="exec",
        side_effect=SideEffectClassification(
            action_class="workspace-mutating",
            rationale="Applies a patch.",
        ),
        approval_explanation={
            "approval_required": True,
            "policy_preset": "ask",
            "rationale": "Workspace mutation requires operator approval.",
        },
    )

    payload = metadata.as_payload()

    assert payload["approval_explanation"] == {
        "approval_required": True,
        "policy_preset": "ask",
        "rationale": "Workspace mutation requires operator approval.",
    }


def test_token_budget_telemetry_is_metadata_only_and_validates_counts() -> None:
    telemetry = TokenBudgetTelemetry(
        budget_id="budget-coding-1",
        source="profile",
        observed_prompt_tokens=100,
        observed_completion_tokens=50,
        observed_total_tokens=150,
        remaining_tokens=850,
        warning="below-soft-limit",
    )

    assert telemetry.as_payload() == {
        "budget_id": "budget-coding-1",
        "source": "profile",
        "observed_prompt_tokens": 100,
        "observed_completion_tokens": 50,
        "observed_total_tokens": 150,
        "remaining_tokens": 850,
        "warning": "below-soft-limit",
    }

    with pytest.raises(ValueError, match="token counts must be non-negative"):
        TokenBudgetTelemetry(source="caller", observed_total_tokens=-1)
