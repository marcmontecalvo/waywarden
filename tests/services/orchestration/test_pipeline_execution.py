"""Tests for pipeline execution over RT-002 orchestration milestones."""

from __future__ import annotations

from datetime import UTC, datetime

from waywarden.domain.handoff import RunCorrelation
from waywarden.domain.ids import RunId
from waywarden.domain.pipeline import (
    Pipeline,
    PipelineNode,
    PipelineRoute,
    ReviewCheckpoint,
)
from waywarden.services.orchestration.milestones import is_valid_milestone
from waywarden.services.orchestration.pipeline import PipelineExecutionEngine


def _pipeline() -> Pipeline:
    return Pipeline(
        id="coding-review-pipeline",
        start_node="team-run",
        nodes=(
            PipelineNode(
                id="team-run",
                kind="team",
                ref_id="coding-dispatch-team",
                input_artifact_kind="team-handoff",
                output_artifact_kind="team-handoff",
                phase="handoff",
                milestone="team_started",
            ),
            PipelineNode(
                id="review-gate",
                kind="review_checkpoint",
                ref_id="adversarial-review",
                input_artifact_kind="team-handoff",
                output_artifact_kind="review-report",
                phase="review",
                milestone="findings_recorded",
                review_checkpoint=ReviewCheckpoint(
                    input_artifact_kind="team-handoff",
                    passed_output_artifact_kind="approved-handoff",
                    failed_output_artifact_kind="review-findings",
                ),
            ),
            PipelineNode(
                id="fallback-review",
                kind="sub_agent",
                ref_id="agent-reviewer",
                input_artifact_kind="review-findings",
                output_artifact_kind="review-report",
                phase="handoff",
                milestone="sub_agent_started",
            ),
        ),
        routes=(
            PipelineRoute(from_node="team-run", outcome="success", to_node="review-gate"),
            PipelineRoute(from_node="review-gate", outcome="success", to_node=None),
            PipelineRoute(from_node="review-gate", outcome="failure", to_node="fallback-review"),
            PipelineRoute(from_node="fallback-review", outcome="success", to_node=None),
        ),
    )


def test_pipeline_execution_runs_linear_success_path_over_catalog_milestones() -> None:
    engine = PipelineExecutionEngine(now=lambda: datetime(2026, 4, 27, tzinfo=UTC))

    result = engine.execute(
        pipeline=_pipeline(),
        run_id=RunId("run-1"),
        outcomes={"team-run": "success", "review-gate": "success"},
    )

    assert result.status == "completed"
    assert result.visited_node_ids == ("team-run", "review-gate")
    assert [event.payload["milestone"] for event in result.events] == [
        "team_started",
        "findings_recorded",
    ]
    assert all(event.type == "run.progress" for event in result.events)
    assert all(
        is_valid_milestone(str(event.payload["phase"]), str(event.payload["milestone"]))
        for event in result.events
    )


def test_pipeline_execution_branches_on_review_failure() -> None:
    engine = PipelineExecutionEngine(now=lambda: datetime(2026, 4, 27, tzinfo=UTC))
    correlation = RunCorrelation(
        correlation_id="corr-pipeline-1",
        parent_run_id="run-parent",
        child_run_id="run-team",
        dispatcher_run_id="run-parent",
        team_run_id="run-team",
        pipeline_run_id="run-pipeline",
        review_run_id="run-review",
        delegation_id="del-run-parent-1",
        manifest_run_id="run-team",
    )

    result = engine.execute(
        pipeline=_pipeline(),
        run_id=RunId("run-pipeline"),
        outcomes={
            "team-run": "success",
            "review-gate": "failure",
            "fallback-review": "success",
        },
        correlation=correlation,
    )

    assert result.status == "completed"
    assert result.visited_node_ids == ("team-run", "review-gate", "fallback-review")
    assert result.events[0].payload["milestone_ref"] == "handoff.team_started"
    assert result.events[0].payload["run_id"] == "run-pipeline"
    assert result.events[0].payload["parent_run_id"] == "run-parent"
    assert result.events[1].payload["outcome"] == "failure"
    assert result.events[2].payload["node_kind"] == "sub_agent"
    assert result.events[1].payload["milestone_ref"] == "review.findings_recorded"
    assert result.events[1].payload["review_run_id"] == "run-review"


def test_pipeline_execution_aborts_on_abort_route() -> None:
    pipeline = Pipeline(
        id="abort-pipeline",
        start_node="review-gate",
        nodes=(
            PipelineNode(
                id="review-gate",
                kind="review_checkpoint",
                ref_id="adversarial-review",
                input_artifact_kind="team-handoff",
                output_artifact_kind="review-report",
                phase="review",
                milestone="findings_recorded",
                review_checkpoint=ReviewCheckpoint(
                    input_artifact_kind="team-handoff",
                    passed_output_artifact_kind="approved-handoff",
                    failed_output_artifact_kind="review-findings",
                ),
            ),
        ),
        routes=(PipelineRoute(from_node="review-gate", outcome="failure", to_node=None),),
    )
    engine = PipelineExecutionEngine(now=lambda: datetime(2026, 4, 27, tzinfo=UTC))

    result = engine.execute(
        pipeline=pipeline,
        run_id=RunId("run-1"),
        outcomes={"review-gate": "failure"},
    )

    assert result.status == "aborted"
    assert result.visited_node_ids == ("review-gate",)
    assert result.events[0].payload["status"] == "aborted"


def test_pipeline_execution_rejects_unbounded_cycles() -> None:
    pipeline = Pipeline(
        id="retry-pipeline",
        start_node="review-gate",
        nodes=(
            PipelineNode(
                id="review-gate",
                kind="review_checkpoint",
                ref_id="adversarial-review",
                input_artifact_kind="team-handoff",
                output_artifact_kind="review-report",
                phase="review",
                milestone="findings_recorded",
                review_checkpoint=ReviewCheckpoint(
                    input_artifact_kind="team-handoff",
                    passed_output_artifact_kind="approved-handoff",
                    failed_output_artifact_kind="review-findings",
                ),
            ),
        ),
        routes=(PipelineRoute(from_node="review-gate", outcome="failure", to_node="review-gate"),),
    )
    engine = PipelineExecutionEngine(now=lambda: datetime(2026, 4, 27, tzinfo=UTC))

    try:
        engine.execute(
            pipeline=pipeline,
            run_id=RunId("run-1"),
            outcomes={"review-gate": "failure"},
            max_steps=2,
        )
    except ValueError as exc:
        assert "max_steps" in str(exc)
    else:
        raise AssertionError("expected cyclic pipeline execution to be bounded")
