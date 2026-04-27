"""Unit tests for the provider-neutral pipeline primitive."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Any, cast

import pytest

from waywarden.domain.pipeline import (
    Pipeline,
    PipelineNode,
    PipelineRegistry,
    PipelineRoute,
    ReviewCheckpoint,
)


def test_pipeline_chains_team_to_review_checkpoint_with_typed_artifacts() -> None:
    pipeline = Pipeline(
        id="coding-review-pipeline",
        start_node="team-run",
        nodes=(
            PipelineNode(
                id="team-run",
                kind="team",
                ref_id="coding-dispatch-team",
                input_artifact_kind="coding-task",
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
        ),
        routes=(
            PipelineRoute(from_node="team-run", outcome="success", to_node="review-gate"),
            PipelineRoute(from_node="review-gate", outcome="success", to_node=None),
            PipelineRoute(from_node="review-gate", outcome="failure", to_node="team-run"),
        ),
    )

    assert pipeline.node("team-run").kind == "team"
    assert pipeline.node("review-gate").review_checkpoint is not None
    assert pipeline.route("review-gate", "failure").to_node == "team-run"


def test_pipeline_rejects_uncataloged_progress_milestones() -> None:
    with pytest.raises(ValueError, match="cataloged"):
        PipelineNode(
            id="bad-node",
            kind="team",
            ref_id="coding-dispatch-team",
            input_artifact_kind="coding-task",
            output_artifact_kind="team-handoff",
            phase="handoff",
            milestone="pipeline_started",
        )


def test_review_checkpoint_requires_matching_typed_boundary() -> None:
    with pytest.raises(ValueError, match="review checkpoint input"):
        PipelineNode(
            id="review-gate",
            kind="review_checkpoint",
            ref_id="adversarial-review",
            input_artifact_kind="team-handoff",
            output_artifact_kind="review-report",
            phase="review",
            milestone="findings_recorded",
            review_checkpoint=ReviewCheckpoint(
                input_artifact_kind="different-kind",
                passed_output_artifact_kind="approved-handoff",
                failed_output_artifact_kind="review-findings",
            ),
        )


def test_pipeline_rejects_unknown_route_targets_and_duplicate_outcomes() -> None:
    node = PipelineNode(
        id="team-run",
        kind="team",
        ref_id="coding-dispatch-team",
        input_artifact_kind="coding-task",
        output_artifact_kind="team-handoff",
        phase="handoff",
        milestone="team_started",
    )

    with pytest.raises(ValueError, match="unknown to_node"):
        Pipeline(
            id="bad-pipeline",
            start_node="team-run",
            nodes=(node,),
            routes=(PipelineRoute(from_node="team-run", outcome="success", to_node="missing"),),
        )

    with pytest.raises(ValueError, match="duplicate route"):
        Pipeline(
            id="bad-pipeline",
            start_node="team-run",
            nodes=(node,),
            routes=(
                PipelineRoute(from_node="team-run", outcome="success", to_node=None),
                PipelineRoute(from_node="team-run", outcome="success", to_node=None),
            ),
        )


def test_pipeline_registry_registers_and_lists_deterministically() -> None:
    first = Pipeline(
        id="pipeline-a",
        start_node="team-run",
        nodes=(
            PipelineNode(
                id="team-run",
                kind="team",
                ref_id="team-a",
                input_artifact_kind="task",
                output_artifact_kind="handoff",
                phase="handoff",
                milestone="team_started",
            ),
        ),
    )
    second = Pipeline(
        id="pipeline-b",
        start_node="team-run",
        nodes=(
            PipelineNode(
                id="team-run",
                kind="team",
                ref_id="team-b",
                input_artifact_kind="task",
                output_artifact_kind="handoff",
                phase="handoff",
                milestone="team_started",
            ),
        ),
    )

    registry = PipelineRegistry((second, first))

    assert registry.get("pipeline-a") == first
    assert registry.list() == (first, second)
    with pytest.raises(FrozenInstanceError):
        cast(Any, first).id = "other"
