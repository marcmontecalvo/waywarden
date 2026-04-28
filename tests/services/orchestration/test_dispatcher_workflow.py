"""Tests for dispatcher workflow packaging and normalized handoff artifacts."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from waywarden.assets.loader import AssetRegistry
from waywarden.assets.schema import WorkflowHandoffMetadata, WorkflowMetadata
from waywarden.domain.handoff import HandoffArtifact, RunCorrelation
from waywarden.domain.ids import RunId
from waywarden.domain.manifest.input_mount import InputMount
from waywarden.domain.manifest.manifest import WorkspaceManifest
from waywarden.domain.manifest.network_policy import NetworkPolicy
from waywarden.domain.manifest.output_contract import OutputContract
from waywarden.domain.manifest.secret_scope import SecretScope
from waywarden.domain.manifest.snapshot_policy import SnapshotPolicy
from waywarden.domain.manifest.tool_policy import ToolPolicy
from waywarden.domain.manifest.writable_path import WritablePath
from waywarden.domain.pipeline import Pipeline, PipelineNode, PipelineRoute, ReviewCheckpoint
from waywarden.domain.subagent import SubAgent, SubAgentRole
from waywarden.domain.team import Team, TeamHandoffRoute
from waywarden.services.orchestration.dispatcher_workflow import DispatcherWorkflowPackager
from waywarden.services.orchestration.pipeline import PipelineExecutionEngine
from waywarden.services.orchestration.subagent_progress import make_sub_agent_progress_event
from waywarden.services.orchestration.team_progress import make_team_progress_event


def _manifest() -> WorkspaceManifest:
    return WorkspaceManifest(
        run_id=RunId("run-dispatch-parent"),
        inputs=[
            InputMount(
                name="repo",
                kind="directory",
                source_ref="artifact://workspace/repo",
                target_path="/workspace/repo",
                read_only=True,
            )
        ],
        writable_paths=[
            WritablePath(
                path="/workspace/output",
                purpose="declared-output",
                retention="artifact-promoted",
            )
        ],
        outputs=[
            OutputContract(
                name="plan",
                path="/workspace/output/plan.md",
                kind="file",
                required=True,
            ),
            OutputContract(
                name="patch",
                path="/workspace/output/changes.patch",
                kind="patch-set",
                required=True,
            ),
            OutputContract(
                name="review",
                path="/workspace/output/review.md",
                kind="report",
                required=False,
            ),
        ],
        network_policy=NetworkPolicy(mode="deny", allow=[], deny=[]),
        tool_policy=ToolPolicy(preset="ask", rules=[], default_decision="approval-required"),
        secret_scope=SecretScope(
            mode="none",
            allowed_secret_refs=[],
            mount_env=[],
            redaction_level="full",
        ),
        snapshot_policy=SnapshotPolicy(
            on_start=False,
            on_completion=True,
            on_failure=True,
            before_destructive_actions=True,
            max_snapshots=3,
            include_paths=[],
            exclude_paths=[],
        ),
    )


def _team() -> Team:
    dispatcher = SubAgent(
        id="agent-dispatcher",
        role=SubAgentRole(
            name="dispatcher",
            objective="Route coding work to the right specialists.",
            responsibilities=("route implementation",),
            constraints=("stay within workflow bounds",),
            expected_outputs=("team-handoff", "needs-review", "needs-tests"),
        ),
    )
    reviewer = SubAgent(
        id="agent-reviewer",
        role=SubAgentRole(
            name="reviewer",
            objective="Review bounded implementation work.",
            responsibilities=("review patch",),
            constraints=("report defects only",),
            expected_outputs=("review-report",),
        ),
    )
    tester = SubAgent(
        id="agent-tester",
        role=SubAgentRole(
            name="tester",
            objective="Test bounded implementation work.",
            responsibilities=("run tests",),
            constraints=("stay within test scope",),
            expected_outputs=("test-report",),
        ),
    )
    return Team(
        id="coding-dispatch-team",
        input_artifact_kind="team-handoff",
        output_artifact_kind="team-handoff",
        dispatcher=dispatcher,
        specialists=(reviewer, tester),
        handoff_routes=(
            TeamHandoffRoute(
                from_agent="agent-dispatcher",
                output_name="needs-review",
                to_agent="agent-reviewer",
                artifact_kind="review-request",
            ),
            TeamHandoffRoute(
                from_agent="agent-dispatcher",
                output_name="needs-tests",
                to_agent="agent-tester",
                artifact_kind="test-request",
            ),
        ),
        fallback_agent="agent-reviewer",
    )


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


@pytest.mark.anyio
async def test_dispatcher_workflow_asset_loads_with_typed_handoff_contract() -> None:
    registry = AssetRegistry()
    await registry.load_from_dir("assets/workflows/coding-dispatcher-workflow")
    asset = registry.get("coding-dispatcher-workflow", kind="workflow")

    assert isinstance(asset, WorkflowMetadata)
    assert asset.workflow_type == "dispatcher"
    assert asset.dispatcher == "agent-dispatcher"
    assert asset.team_ref == "coding-dispatch-team"
    assert asset.pipeline_ref == "coding-review-pipeline"
    assert asset.handoff_artifact.artifact_kind == "team-handoff"
    assert asset.expected_outputs == ("plan", "patch", "review")


def test_dispatcher_workflow_round_trip_preserves_normalized_handoff_artifact() -> None:
    workflow = WorkflowMetadata(
        id="coding-dispatcher-workflow",
        kind="workflow",
        version="1.0.0",
        description="Dispatcher workflow packaging.",
        workflow_type="dispatcher",
        dispatcher="agent-dispatcher",
        team_ref="coding-dispatch-team",
        pipeline_ref="coding-review-pipeline",
        handoff_artifact=WorkflowHandoffMetadata(
            artifact_kind="team-handoff",
            label="Coding team handoff",
            output_name="team-handoff",
        ),
        expected_outputs=("plan", "patch", "review"),
    )
    correlation = RunCorrelation(
        correlation_id="corr-coding-1",
        parent_run_id="run-dispatch-parent",
        child_run_id="run-team-child",
        dispatcher_run_id="run-dispatch-parent",
        team_run_id="run-team-child",
        pipeline_run_id="run-pipeline-child",
        review_run_id="run-review-child",
        sub_agent_run_id="run-reviewer-child",
        delegation_id="del-run-dispatch-parent-1",
        manifest_run_id="run-team-child",
    )
    packager = DispatcherWorkflowPackager(now=lambda: datetime(2026, 4, 27, tzinfo=UTC))

    package = packager.package(
        workflow=workflow,
        parent_manifest=_manifest(),
        objective="Implement a bounded code change",
        correlation=correlation,
        artifact_ref="artifact://runs/run-dispatch-parent/team-handoff",
    )

    assert package.envelope.child_manifest.run_id == RunId("run-team-child")
    assert package.handoff_artifact.child_run_id == RunId("run-team-child")
    assert package.handoff_artifact.delegation_id == package.envelope.id
    assert package.handoff_artifact.manifest_run_id == package.envelope.child_manifest.run_id

    team = _team()
    pipeline = _pipeline()
    assert team.accepts_handoff_artifact(package.handoff_artifact) is True
    assert pipeline.accepts_handoff_artifact(package.handoff_artifact) is True
    assert package.handoff_artifact.artifact_kind == "team-handoff"
    assert package.handoff_artifact.output_name == "team-handoff"


def test_dispatcher_workflow_emits_rt002_metadata_with_correlation_ids() -> None:
    workflow = WorkflowMetadata(
        id="coding-dispatcher-workflow",
        kind="workflow",
        version="1.0.0",
        description="Dispatcher workflow packaging.",
        workflow_type="dispatcher",
        dispatcher="agent-dispatcher",
        team_ref="coding-dispatch-team",
        pipeline_ref="coding-review-pipeline",
        handoff_artifact=WorkflowHandoffMetadata(
            artifact_kind="team-handoff",
            label="Coding team handoff",
            output_name="team-handoff",
        ),
        expected_outputs=("plan", "patch", "review"),
    )
    correlation = RunCorrelation(
        correlation_id="corr-coding-1",
        parent_run_id="run-dispatch-parent",
        child_run_id="run-team-child",
        dispatcher_run_id="run-dispatch-parent",
        team_run_id="run-team-child",
        pipeline_run_id="run-pipeline-child",
        review_run_id="run-review-child",
        sub_agent_run_id="run-reviewer-child",
        delegation_id="del-run-dispatch-parent-1",
        manifest_run_id="run-team-child",
    )
    packager = DispatcherWorkflowPackager(now=lambda: datetime(2026, 4, 27, tzinfo=UTC))

    package = packager.package(
        workflow=workflow,
        parent_manifest=_manifest(),
        objective="Implement a bounded code change",
        correlation=correlation,
        artifact_ref="artifact://runs/run-dispatch-parent/team-handoff",
    )

    progress_payload = package.progress_event.payload
    artifact_payload = package.artifact_event.payload
    assert progress_payload["phase"] == "handoff"
    assert progress_payload["milestone"] == "envelope_emitted"
    assert progress_payload["milestone_ref"] == "handoff.envelope_emitted"
    assert progress_payload["run_id"] == "run-dispatch-parent"
    assert progress_payload["correlation_id"] == "corr-coding-1"
    assert progress_payload["team_run_id"] == "run-team-child"
    assert progress_payload["pipeline_run_id"] == "run-pipeline-child"
    assert progress_payload["review_run_id"] == "run-review-child"
    assert artifact_payload["delegation_id"] == str(package.envelope.id)
    assert artifact_payload["manifest_run_id"] == "run-team-child"
    assert artifact_payload["source_run_id"] == "run-dispatch-parent"
    assert artifact_payload["target_run_id"] == "run-team-child"
    assert artifact_payload["handoff_boundary"] == "dispatcher_to_team"

    team_event = make_team_progress_event(
        run_id=RunId("run-team-child"),
        team=_team(),
        seq=1,
        milestone="team_started",
        status="running",
        summary="Team started",
        member_statuses={
            "agent-dispatcher": "completed",
            "agent-reviewer": "running",
            "agent-tester": "registered",
        },
        now=datetime(2026, 4, 27, tzinfo=UTC),
        correlation=correlation,
    )
    pipeline_event = (
        PipelineExecutionEngine(now=lambda: datetime(2026, 4, 27, tzinfo=UTC))
        .execute(
            pipeline=_pipeline(),
            run_id=RunId("run-pipeline-child"),
            outcomes={
                "team-run": "success",
                "review-gate": "failure",
                "fallback-review": "success",
            },
            correlation=correlation,
        )
        .events[1]
    )
    sub_agent_event = make_sub_agent_progress_event(
        run_id=RunId("run-reviewer-child"),
        sub_agent=_team().specialists[0],
        seq=1,
        milestone="sub_agent_started",
        status="running",
        summary="Reviewer started",
        now=datetime(2026, 4, 27, tzinfo=UTC),
        correlation=correlation,
    )

    for event in (team_event, pipeline_event, sub_agent_event):
        assert event.payload["correlation_id"] == "corr-coding-1"
        assert event.payload["dispatcher_run_id"] == "run-dispatch-parent"
        assert event.payload["team_run_id"] == "run-team-child"
        assert event.payload["pipeline_run_id"] == "run-pipeline-child"


def test_handoff_artifact_requires_artifact_scheme() -> None:
    with pytest.raises(ValueError, match="artifact://"):
        HandoffArtifact(
            artifact_ref="runs/run-1/team-handoff",
            artifact_kind="team-handoff",
            label="Coding team handoff",
            output_name="team-handoff",
            producer_run_id="run-dispatch-parent",
            parent_run_id="run-dispatch-parent",
            child_run_id="run-team-child",
            delegation_id="del-run-dispatch-parent-1",
            manifest_run_id="run-team-child",
            correlation_id="corr-coding-1",
        )
