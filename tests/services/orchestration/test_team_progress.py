"""Tests for team-level RT-002 progress aggregation."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

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

    event = make_team_progress_event(
        run_id=RunId("run-1"),
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
        now=datetime(2026, 4, 27, tzinfo=UTC),
    )

    assert event.type == "run.progress"
    assert event.payload["phase"] == "handoff"
    assert event.payload["milestone"] == "team_started"
    assert event.payload["team_id"] == "coding-team"
    assert event.payload["status"] == "running"
    assert event.payload["member_statuses"] == {
        "agent-dispatcher": "completed",
        "agent-reviewer": "running",
        "agent-tester": "registered",
    }
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
