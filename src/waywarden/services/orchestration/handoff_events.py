"""Helpers for RT-002 artifact events emitted at handoff boundaries."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from waywarden.domain.handoff import HandoffArtifact, RunCorrelation
from waywarden.domain.ids import RunEventId, RunId
from waywarden.domain.run_event import Actor, Causation, RunEvent


def make_handoff_artifact_event(
    *,
    run_id: RunId,
    handoff_artifact: HandoffArtifact,
    seq: int,
    source_run_id: RunId | str,
    target_run_id: RunId | str,
    handoff_boundary: str,
    correlation: RunCorrelation | None = None,
    source_agent_id: str | None = None,
    target_agent_id: str | None = None,
    now: datetime | None = None,
) -> RunEvent:
    """Build a ``run.artifact_created`` event for a typed handoff boundary."""
    boundary = handoff_boundary.strip()
    if not boundary:
        raise ValueError("handoff_boundary must not be blank")
    clean_source_run_id = str(source_run_id).strip()
    clean_target_run_id = str(target_run_id).strip()
    if not clean_source_run_id:
        raise ValueError("source_run_id must not be blank")
    if not clean_target_run_id:
        raise ValueError("target_run_id must not be blank")
    if correlation is not None and handoff_artifact.correlation_id != correlation.correlation_id:
        raise ValueError("handoff_artifact correlation_id must match correlation")

    timestamp = now or datetime.now(UTC)
    payload: dict[str, object] = {
        "artifact_ref": handoff_artifact.artifact_ref,
        "artifact_kind": handoff_artifact.artifact_kind,
        "label": handoff_artifact.label,
        "source_run_id": clean_source_run_id,
        "target_run_id": clean_target_run_id,
        "handoff_boundary": boundary,
        "producer_run_id": str(handoff_artifact.producer_run_id),
        "parent_run_id": str(handoff_artifact.parent_run_id),
        "child_run_id": str(handoff_artifact.child_run_id),
        "delegation_id": str(handoff_artifact.delegation_id),
        "manifest_run_id": str(handoff_artifact.manifest_run_id),
        "correlation_id": handoff_artifact.correlation_id,
    }
    if source_agent_id is not None:
        payload["source_agent_id"] = source_agent_id
    if target_agent_id is not None:
        payload["target_agent_id"] = target_agent_id
    if correlation is not None:
        payload.update(correlation.as_payload())

    return RunEvent(
        id=RunEventId(f"evt-{run_id}-artifact-{uuid4().hex}"),
        run_id=run_id,
        seq=seq,
        type="run.artifact_created",
        payload=payload,
        timestamp=timestamp,
        causation=Causation(
            event_id=None,
            action=f"handoff_artifact.{boundary}",
            request_id=str(handoff_artifact.delegation_id),
        ),
        actor=Actor(kind="system", id=str(run_id), display="handoff"),
    )


__all__ = ["make_handoff_artifact_event"]
