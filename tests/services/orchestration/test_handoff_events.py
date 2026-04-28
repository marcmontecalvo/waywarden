"""Tests for RT-002 handoff artifact events across orchestration boundaries."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from waywarden.domain.handoff import HandoffArtifact, RunCorrelation
from waywarden.domain.ids import RunId
from waywarden.services.orchestration.handoff_events import make_handoff_artifact_event


def _handoff_artifact() -> HandoffArtifact:
    return HandoffArtifact(
        artifact_ref="artifact://runs/run-parent/team-handoff",
        artifact_kind="team-handoff",
        label="Coding team handoff",
        output_name="team-handoff",
        producer_run_id="run-parent",
        parent_run_id="run-parent",
        child_run_id="run-team",
        delegation_id="del-run-parent-1",
        manifest_run_id="run-team",
        correlation_id="corr-handoff-1",
    )


def _correlation() -> RunCorrelation:
    return RunCorrelation(
        correlation_id="corr-handoff-1",
        parent_run_id="run-parent",
        child_run_id="run-team",
        dispatcher_run_id="run-parent",
        team_run_id="run-team",
        pipeline_run_id="run-pipeline",
        review_run_id="run-review",
        sub_agent_run_id="run-reviewer",
        delegation_id="del-run-parent-1",
        manifest_run_id="run-team",
    )


@pytest.mark.parametrize(
    ("handoff_boundary", "source_run_id", "target_run_id", "source_agent_id", "target_agent_id"),
    [
        ("sub_agent_to_team", "run-reviewer", "run-team", "agent-reviewer", "coding-team"),
        ("team_to_pipeline", "run-team", "run-pipeline", "coding-team", "coding-review-pipeline"),
        ("pipeline_to_review", "run-pipeline", "run-review", "coding-review-pipeline", None),
    ],
)
def test_handoff_artifact_events_link_source_and_target_runs(
    handoff_boundary: str,
    source_run_id: str,
    target_run_id: str,
    source_agent_id: str,
    target_agent_id: str | None,
) -> None:
    event = make_handoff_artifact_event(
        run_id=RunId(source_run_id),
        handoff_artifact=_handoff_artifact(),
        seq=4,
        source_run_id=source_run_id,
        target_run_id=target_run_id,
        handoff_boundary=handoff_boundary,
        source_agent_id=source_agent_id,
        target_agent_id=target_agent_id,
        correlation=_correlation(),
        now=datetime(2026, 4, 28, tzinfo=UTC),
    )

    assert event.type == "run.artifact_created"
    assert event.payload["artifact_ref"] == "artifact://runs/run-parent/team-handoff"
    assert event.payload["source_run_id"] == source_run_id
    assert event.payload["target_run_id"] == target_run_id
    assert event.payload["handoff_boundary"] == handoff_boundary
    assert event.payload["parent_run_id"] == "run-parent"
    assert event.payload["child_run_id"] == "run-team"
    assert event.payload["pipeline_run_id"] == "run-pipeline"
    assert event.payload["review_run_id"] == "run-review"
    assert event.payload["source_agent_id"] == source_agent_id
    if target_agent_id is None:
        assert "target_agent_id" not in event.payload
    else:
        assert event.payload["target_agent_id"] == target_agent_id


def test_handoff_artifact_event_rejects_blank_boundary() -> None:
    with pytest.raises(ValueError, match="handoff_boundary"):
        make_handoff_artifact_event(
            run_id=RunId("run-parent"),
            handoff_artifact=_handoff_artifact(),
            seq=1,
            source_run_id="run-parent",
            target_run_id="run-team",
            handoff_boundary=" ",
        )


def test_handoff_artifact_event_rejects_mismatched_correlation() -> None:
    with pytest.raises(ValueError, match="correlation_id"):
        make_handoff_artifact_event(
            run_id=RunId("run-parent"),
            handoff_artifact=_handoff_artifact(),
            seq=1,
            source_run_id="run-parent",
            target_run_id="run-team",
            handoff_boundary="dispatcher_to_team",
            correlation=RunCorrelation(
                correlation_id="corr-other",
                parent_run_id="run-parent",
                child_run_id="run-team",
                dispatcher_run_id="run-parent",
                team_run_id="run-team",
                pipeline_run_id="run-pipeline",
                delegation_id="del-run-parent-1",
                manifest_run_id="run-team",
            ),
        )
