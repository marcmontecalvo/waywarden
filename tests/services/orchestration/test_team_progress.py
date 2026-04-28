"""Tests for team-level RT-002 progress aggregation."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from waywarden.domain.durability import (
    SideEffectClassification,
    TokenBudgetTelemetry,
    ToolActionMetadata,
)
from waywarden.domain.handoff import RunCorrelation
from waywarden.domain.ids import RunId
from waywarden.domain.subagent import SubAgent, SubAgentRole
from waywarden.domain.team import Team
from waywarden.services.orchestration.milestones import is_valid_milestone
from waywarden.services.orchestration.team_progress import make_team_progress_event


def _agent(agent_id: str, name: str) -> SubAgent:
    return SubAgent(
        id=agent_id,
        role=SubAgentRole(
            name=name,
            objective=f"Own {name} work.",
            responsibilities=(f"handle {name}",),
            constraints=("stay bounded",),
            expected_outputs=(f"{name}-output",),
        ),
    )


def test_team_progress_event_aggregates_per_agent_status() -> None:
    team = Team(
        id="coding-team",
        input_artifact_kind="team-handoff",
        output_artifact_kind="team-handoff",
        dispatcher=_agent("agent-dispatcher", "dispatcher"),
        specialists=(
            _agent("agent-reviewer", "reviewer"),
            _agent("agent-tester", "tester"),
        ),
    )

    correlation = RunCorrelation(
        correlation_id="corr-team-1",
        parent_run_id="run-parent",
        child_run_id="run-team",
        dispatcher_run_id="run-parent",
        team_run_id="run-team",
        pipeline_run_id="run-pipeline",
        delegation_id="del-run-parent-1",
        manifest_run_id="run-team",
    )
    event = make_team_progress_event(
        run_id=RunId("run-team"),
        team=team,
        seq=7,
        milestone="team_started",
        status="running",
        summary="Team started",
        member_statuses={
            "agent-dispatcher": "completed",
            "agent-reviewer": "running",
            "agent-tester": "registered",
        },
        member_run_ids={
            "agent-dispatcher": "run-team-dispatcher",
            "agent-reviewer": "run-team-reviewer",
            "agent-tester": "run-team-tester",
        },
        correlation=correlation,
        token_budget=TokenBudgetTelemetry(
            budget_id="budget-team-1",
            source="profile",
            observed_total_tokens=200,
            remaining_tokens=800,
            warning="below-soft-limit",
        ),
        tool_actions=(
            ToolActionMetadata(
                tool_id="shell",
                action="exec",
                side_effect=SideEffectClassification(
                    action_class="workspace-mutating",
                    rationale="Team member applies workspace edits.",
                ),
                approval_explanation={
                    "approval_required": True,
                    "policy_preset": "ask",
                    "rationale": "Workspace mutation routes through policy.",
                },
            ),
        ),
        now=datetime(2026, 4, 27, tzinfo=UTC),
    )

    assert event.type == "run.progress"
    assert event.payload["phase"] == "handoff"
    assert event.payload["milestone"] == "team_started"
    assert event.payload["milestone_ref"] == "handoff.team_started"
    assert event.payload["run_id"] == "run-team"
    assert event.payload["team_id"] == "coding-team"
    assert event.payload["status"] == "running"
    assert event.payload["member_statuses"] == {
        "agent-dispatcher": "completed",
        "agent-reviewer": "running",
        "agent-tester": "registered",
    }
    assert event.payload["agent_progress"] == (
        {
            "agent_id": "agent-dispatcher",
            "run_id": "run-team-dispatcher",
            "parent_run_id": "run-parent",
            "status": "completed",
            "milestone_ref": "handoff.team_started",
        },
        {
            "agent_id": "agent-reviewer",
            "run_id": "run-team-reviewer",
            "parent_run_id": "run-parent",
            "status": "running",
            "milestone_ref": "handoff.team_started",
        },
        {
            "agent_id": "agent-tester",
            "run_id": "run-team-tester",
            "parent_run_id": "run-parent",
            "status": "registered",
            "milestone_ref": "handoff.team_started",
        },
    )
    assert event.payload["token_budget"] == {
        "budget_id": "budget-team-1",
        "source": "profile",
        "observed_prompt_tokens": None,
        "observed_completion_tokens": None,
        "observed_total_tokens": 200,
        "remaining_tokens": 800,
        "warning": "below-soft-limit",
    }
    assert event.payload["tool_actions"] == (
        {
            "tool_id": "shell",
            "action": "exec",
            "side_effect": {
                "action_class": "workspace-mutating",
                "rationale": "Team member applies workspace edits.",
            },
            "approval_explanation": {
                "approval_required": True,
                "policy_preset": "ask",
                "rationale": "Workspace mutation routes through policy.",
            },
        },
    )
    assert is_valid_milestone(str(event.payload["phase"]), str(event.payload["milestone"]))


def test_team_progress_rejects_unknown_member_statuses() -> None:
    team = Team(
        id="coding-team",
        input_artifact_kind="team-handoff",
        output_artifact_kind="team-handoff",
        dispatcher=_agent("agent-dispatcher", "dispatcher"),
        specialists=(_agent("agent-reviewer", "reviewer"),),
    )

    with pytest.raises(ValueError, match="unknown team member"):
        make_team_progress_event(
            run_id=RunId("run-1"),
            team=team,
            seq=1,
            milestone="team_started",
            status="running",
            summary="Team started",
            member_statuses={"agent-other": "running"},
        )


def test_team_progress_rejects_missing_member_statuses() -> None:
    team = Team(
        id="coding-team",
        input_artifact_kind="team-handoff",
        output_artifact_kind="team-handoff",
        dispatcher=_agent("agent-dispatcher", "dispatcher"),
        specialists=(_agent("agent-reviewer", "reviewer"),),
    )

    with pytest.raises(ValueError, match="missing team member"):
        make_team_progress_event(
            run_id=RunId("run-1"),
            team=team,
            seq=1,
            milestone="team_started",
            status="running",
            summary="Team started",
            member_statuses={"agent-dispatcher": "running"},
        )


def test_team_progress_rejects_missing_member_run_ids() -> None:
    team = Team(
        id="coding-team",
        input_artifact_kind="team-handoff",
        output_artifact_kind="team-handoff",
        dispatcher=_agent("agent-dispatcher", "dispatcher"),
        specialists=(_agent("agent-reviewer", "reviewer"),),
    )

    with pytest.raises(ValueError, match="missing team member run ids"):
        make_team_progress_event(
            run_id=RunId("run-1"),
            team=team,
            seq=1,
            milestone="team_started",
            status="running",
            summary="Team started",
            member_statuses={
                "agent-dispatcher": "running",
                "agent-reviewer": "registered",
            },
            member_run_ids={"agent-dispatcher": "run-dispatcher"},
        )


def test_team_progress_rejects_blank_member_run_id() -> None:
    team = Team(
        id="coding-team",
        input_artifact_kind="team-handoff",
        output_artifact_kind="team-handoff",
        dispatcher=_agent("agent-dispatcher", "dispatcher"),
        specialists=(_agent("agent-reviewer", "reviewer"),),
    )

    with pytest.raises(ValueError, match="must not be blank"):
        make_team_progress_event(
            run_id=RunId("run-1"),
            team=team,
            seq=1,
            milestone="team_started",
            status="running",
            summary="Team started",
            member_statuses={
                "agent-dispatcher": "running",
                "agent-reviewer": "registered",
            },
            member_run_ids={
                "agent-dispatcher": "run-dispatcher",
                "agent-reviewer": " ",
            },
        )
