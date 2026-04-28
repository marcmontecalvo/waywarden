"""Dispatcher workflow packaging over delegation envelopes and RT-002 metadata."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from waywarden.assets.schema import WorkflowMetadata
from waywarden.domain.delegation.envelope import DelegationEnvelope, make_envelope
from waywarden.domain.delegation.narrowing import narrow_manifest
from waywarden.domain.handoff import HandoffArtifact, RunCorrelation
from waywarden.domain.ids import RunEventId, RunId
from waywarden.domain.manifest.manifest import WorkspaceManifest
from waywarden.domain.run_event import Actor, Causation, RunEvent
from waywarden.services.orchestration.handoff_events import make_handoff_artifact_event


@dataclass(frozen=True, slots=True)
class DispatcherWorkflowPackage:
    """Typed dispatch package emitted by a dispatcher workflow."""

    envelope: DelegationEnvelope
    handoff_artifact: HandoffArtifact
    correlation: RunCorrelation
    progress_event: RunEvent
    artifact_event: RunEvent


class DispatcherWorkflowPackager:
    """Create normalized dispatcher handoff packages with RT-002 metadata."""

    def __init__(self, *, now: Callable[[], datetime] | None = None) -> None:
        self._now = now or (lambda: datetime.now(UTC))

    def package(
        self,
        *,
        workflow: WorkflowMetadata,
        parent_manifest: WorkspaceManifest,
        objective: str,
        correlation: RunCorrelation,
        artifact_ref: str,
    ) -> DispatcherWorkflowPackage:
        child_manifest = _narrow_child_manifest(
            parent_manifest=parent_manifest,
            child_run_id=RunId(str(correlation.child_run_id)),
            expected_outputs=workflow.expected_outputs,
        )
        narrow_manifest(parent_manifest, child_manifest)
        envelope = make_envelope(
            parent_run_id=RunId(str(correlation.parent_run_id)),
            child_manifest=child_manifest,
            brief=f"Dispatcher handoff: {objective}",
            expected_outputs=workflow.expected_outputs,
        )
        if str(envelope.id) != str(correlation.delegation_id):
            raise ValueError("correlation delegation_id must match the emitted delegation envelope")

        handoff_artifact = HandoffArtifact(
            artifact_ref=artifact_ref,
            artifact_kind=workflow.handoff_artifact.artifact_kind,
            label=workflow.handoff_artifact.label,
            output_name=workflow.handoff_artifact.output_name,
            producer_run_id=correlation.dispatcher_run_id,
            parent_run_id=correlation.parent_run_id,
            child_run_id=correlation.child_run_id,
            delegation_id=envelope.id,
            manifest_run_id=child_manifest.run_id,
            correlation_id=correlation.correlation_id,
            metadata={
                "workflow_id": workflow.id,
                "team_ref": workflow.team_ref,
                "pipeline_ref": workflow.pipeline_ref,
            },
        )
        progress_event = self._make_progress_event(
            workflow=workflow,
            correlation=correlation,
            handoff_artifact=handoff_artifact,
        )
        artifact_event = self._make_artifact_event(
            correlation=correlation,
            handoff_artifact=handoff_artifact,
        )
        return DispatcherWorkflowPackage(
            envelope=envelope,
            handoff_artifact=handoff_artifact,
            correlation=correlation,
            progress_event=progress_event,
            artifact_event=artifact_event,
        )

    def _make_progress_event(
        self,
        *,
        workflow: WorkflowMetadata,
        correlation: RunCorrelation,
        handoff_artifact: HandoffArtifact,
    ) -> RunEvent:
        payload: dict[str, object] = {
            "phase": "handoff",
            "milestone": "envelope_emitted",
            "milestone_ref": "handoff.envelope_emitted",
            "run_id": str(correlation.dispatcher_run_id),
            "detail": {
                "workflow_id": workflow.id,
                "team_ref": workflow.team_ref,
                "pipeline_ref": workflow.pipeline_ref,
                "handoff_artifact_ref": handoff_artifact.artifact_ref,
            },
        }
        payload.update(correlation.as_payload())
        return RunEvent(
            id=RunEventId(f"evt-{correlation.dispatcher_run_id}-{workflow.id}-{uuid4().hex}"),
            run_id=RunId(str(correlation.dispatcher_run_id)),
            seq=1,
            type="run.progress",
            payload=payload,
            timestamp=self._now(),
            causation=Causation(
                event_id=None,
                action="dispatcher_workflow.package",
                request_id=workflow.id,
            ),
            actor=Actor(kind="system", id=workflow.id, display=workflow.id),
        )

    def _make_artifact_event(
        self,
        *,
        correlation: RunCorrelation,
        handoff_artifact: HandoffArtifact,
    ) -> RunEvent:
        return make_handoff_artifact_event(
            run_id=RunId(str(correlation.dispatcher_run_id)),
            handoff_artifact=handoff_artifact,
            seq=2,
            source_run_id=correlation.dispatcher_run_id,
            target_run_id=correlation.team_run_id,
            handoff_boundary="dispatcher_to_team",
            correlation=correlation,
            now=self._now(),
        )


def _narrow_child_manifest(
    *,
    parent_manifest: WorkspaceManifest,
    child_run_id: RunId,
    expected_outputs: tuple[str, ...],
) -> WorkspaceManifest:
    outputs = tuple(parent_manifest.outputs)
    allowed_outputs = {name for name in expected_outputs}
    child_outputs = [output for output in outputs if output.name in allowed_outputs]
    if len(child_outputs) != len(allowed_outputs):
        found_outputs = {output.name for output in child_outputs}
        missing = sorted(allowed_outputs - found_outputs)
        missing_text = ", ".join(missing)
        raise ValueError(
            f"expected_outputs must reference parent manifest outputs; missing: {missing_text}"
        )
    return WorkspaceManifest(
        run_id=child_run_id,
        inputs=list(parent_manifest.inputs),
        writable_paths=list(parent_manifest.writable_paths),
        outputs=child_outputs,
        network_policy=parent_manifest.network_policy,
        tool_policy=parent_manifest.tool_policy,
        secret_scope=parent_manifest.secret_scope,
        snapshot_policy=parent_manifest.snapshot_policy,
    )
