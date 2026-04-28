"""Tests for sub-agent RT-002 progress emission."""

from __future__ import annotations

from datetime import UTC, datetime

from waywarden.domain.handoff import RunCorrelation
from waywarden.domain.ids import RunId
from waywarden.domain.subagent import (
    SubAgent,
    SubAgentProgressMilestone,
    SubAgentProgressStatus,
    SubAgentRole,
)
from waywarden.services.orchestration.subagent_progress import make_sub_agent_progress_event


def _agent() -> SubAgent:
    return SubAgent(
        id="agent-reviewer",
        role=SubAgentRole(
            name="reviewer",
            objective="Review a bounded patch for correctness.",
            responsibilities=("inspect diff", "report defects"),
            constraints=("do not modify files",),
            expected_outputs=("review-report",),
        ),
    )


def test_sub_agent_run_emits_ordered_progress_with_stable_ids() -> None:
    agent = _agent()
    correlation = RunCorrelation(
        correlation_id="corr-subagent-1",
        parent_run_id="run-parent",
        child_run_id="run-reviewer",
        dispatcher_run_id="run-parent",
        team_run_id="run-team",
        pipeline_run_id="run-pipeline",
        delegation_id="del-run-parent-1",
        manifest_run_id="run-reviewer",
        sub_agent_run_id="run-reviewer",
    )
    milestones: tuple[tuple[SubAgentProgressMilestone, SubAgentProgressStatus, str], ...] = (
        ("sub_agent_registered", "registered", "Reviewer registered"),
        ("sub_agent_started", "running", "Reviewer started"),
        ("sub_agent_completed", "completed", "Reviewer completed"),
    )

    events = tuple(
        make_sub_agent_progress_event(
            run_id=RunId("run-reviewer"),
            sub_agent=agent,
            seq=index,
            milestone=milestone,
            status=status,
            summary=summary,
            correlation=correlation,
            now=datetime(2026, 4, 28, tzinfo=UTC),
        )
        for index, (milestone, status, summary) in enumerate(milestones, start=1)
    )

    assert [event.seq for event in events] == [1, 2, 3]
    assert [event.payload["agent_id"] for event in events] == [
        "agent-reviewer",
        "agent-reviewer",
        "agent-reviewer",
    ]
    assert [event.payload["run_id"] for event in events] == [
        "run-reviewer",
        "run-reviewer",
        "run-reviewer",
    ]
    assert [event.payload["parent_run_id"] for event in events] == [
        "run-parent",
        "run-parent",
        "run-parent",
    ]
    assert [event.payload["milestone_ref"] for event in events] == [
        "handoff.sub_agent_registered",
        "handoff.sub_agent_started",
        "handoff.sub_agent_completed",
    ]
