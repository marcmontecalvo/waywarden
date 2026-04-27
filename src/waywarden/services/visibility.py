"""VisibilityService - read-only snapshot of run progress from RT-002 events.

This module is intentionally a **reader only**: it consumes from
``RunEventRepository``, ``RunRepository``, ``WorkspaceManifestRepository``,
and optionally ``ApprovalRepository`` to assemble a ``RunSnapshot``.
It must never append events.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from waywarden.domain.repositories import (
    ApprovalRepository,
    RunEventRepository,
    RunRepository,
    WorkspaceManifestRepository,
)
from waywarden.services.orchestration.milestones import MILESTONE_CATALOG

# ---------------------------------------------------------------------------
# Domain types for the visibility surface
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MilestoneRecord:
    """A single milestone derived from a ``run.progress`` event."""

    seq: int
    run_id: str
    phase: str
    milestone: str
    description: str
    timestamp: str


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    """A single artifact derived from a ``run.artifact_created`` event."""

    seq: int
    run_id: str
    artifact_kind: str
    artifact_ref: str
    label: str | None
    timestamp: str


@dataclass(frozen=True, slots=True)
class PlanRevisionRecord:
    """A single plan revision derived from ``run.artifact_created(kind=plan-revision)`` events."""

    seq: int
    run_id: str
    version: int
    artifact_ref: str
    diff_from_previous: str
    rationale: str
    timestamp: str


@dataclass(frozen=True, slots=True)
class ManifestSummary:
    """Redacted RT-001 manifest overview (no mutable body)."""

    run_id: str
    tool_policy_preset: str


@dataclass(frozen=True, slots=True)
class PendingApprovalRecord:
    """A single pending approval surfaced in the visibility snapshot."""

    approval_id: str
    approval_kind: str
    summary: str
    requested_at: str
    expires_at: str | None = None


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------


class MilestoneRecordModel(BaseModel):
    seq: int
    run_id: str
    phase: str
    milestone: str
    description: str
    timestamp: str


class ArtifactRecordModel(BaseModel):
    seq: int
    run_id: str
    artifact_kind: str
    artifact_ref: str
    label: str | None
    timestamp: str


class PlanRevisionRecordModel(BaseModel):
    seq: int
    run_id: str
    version: int
    artifact_ref: str
    diff_from_previous: str
    rationale: str
    timestamp: str


class ManifestSummaryModel(BaseModel):
    run_id: str
    tool_policy_preset: str


class PendingApprovalRecordModel(BaseModel):
    approval_id: str
    approval_kind: str
    summary: str
    requested_at: str
    expires_at: str | None = None


class RunSnapshot(BaseModel):
    run_state: str
    milestones: list[MilestoneRecordModel] = []
    artifacts: list[ArtifactRecordModel] = []
    plan_revisions: list[PlanRevisionRecordModel] = []
    pending_approvals: list[PendingApprovalRecordModel] = []
    latest_checkpoint_ref: str | None = None
    manifest_summary: ManifestSummaryModel | None = None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


_MILESTONE_DESCRIPTIONS: frozenset[tuple[str, str]] = frozenset(
    (md.phase, md.milestone) for md in MILESTONE_CATALOG
)

_MILESTONE_DESCRIPTION_MAP: dict[tuple[str, str], str] = {
    (md.phase, md.milestone): md.description for md in MILESTONE_CATALOG
}


class VisibilityService:
    """Read-only snapshot of run progress from RT-002 event log.

    Parameters
    ----------
    events:
        Append-only RT-002 event log repository.
    runs:
        Run record repository.
    manifests:
        Workspace manifest repository.
    """

    def __init__(
        self,
        events: RunEventRepository,
        runs: RunRepository | None = None,
        manifests: WorkspaceManifestRepository | None = None,
        approvals: ApprovalRepository | None = None,
    ) -> None:
        self._events = events
        self._runs = runs
        self._manifests = manifests
        self._approvals = approvals

    async def snapshot(self, run_id: str) -> RunSnapshot:
        """Assemble a ``RunSnapshot`` for *run_id*.

        Returns
        -------
        RunSnapshot
            The current visibility snapshot including:
            - ``run_state`` from the run record
            - ``milestones`` derived 1:1 from ``run.progress`` events
            - ``artifacts`` derived 1:1 from ``run.artifact_created`` events
            - ``pending_approvals`` from the approval repository
            - ``latest_checkpoint_ref`` (N/A for P4, always ``None``)
            - ``manifest_summary`` redacted manifest overview
        """
        milestones: list[MilestoneRecord] = []
        artifacts: list[ArtifactRecord] = []
        plan_revisions: list[PlanRevisionRecord] = []
        run_state: str = "unknown"

        # Load run state if repository available
        if self._runs is not None:
            run = await self._runs.get(run_id)
            if run is not None:
                run_state = run.state

        # Read all events and derive milestones/artifacts
        all_events = await self._events.list(run_id, since_seq=0)
        for ev in all_events:
            if ev.type == "run.progress":
                phase = str(ev.payload.get("phase", ""))
                milestone = str(ev.payload.get("milestone", ""))
                description = _MILESTONE_DESCRIPTION_MAP.get(
                    (phase, milestone), f"{phase}/{milestone}"
                )
                milestones.append(
                    MilestoneRecord(
                        seq=ev.seq,
                        run_id=run_id,
                        phase=phase,
                        milestone=milestone,
                        description=description,
                        timestamp=ev.timestamp.isoformat(),
                    )
                )
            elif ev.type == "run.artifact_created":
                artifact_kind = str(ev.payload.get("artifact_kind", ""))
                if artifact_kind == "plan-revision":
                    plan_revisions.append(
                        PlanRevisionRecord(
                            seq=ev.seq,
                            run_id=run_id,
                            version=int(str(ev.payload.get("version", 0))),
                            artifact_ref=str(ev.payload.get("artifact_ref", "")),
                            diff_from_previous=str(ev.payload.get("diff_from_previous", "")),
                            rationale=str(ev.payload.get("rationale", "")),
                            timestamp=ev.timestamp.isoformat(),
                        )
                    )
                else:
                    artifacts.append(
                        ArtifactRecord(
                            seq=ev.seq,
                            run_id=run_id,
                            artifact_kind=artifact_kind,
                            artifact_ref=str(ev.payload.get("artifact_ref", "")),
                            label=str(ev.payload.get("label")) if "label" in ev.payload else None,
                            timestamp=ev.timestamp.isoformat(),
                        )
                    )

        # Checkpoints - not emitted as RT-002 events, so always None for P4
        latest_checkpoint_ref: str | None = None

        # Pending approvals - surfaced only when the approval
        # repository is wired (P6-6).
        pending_approvals: list[PendingApprovalRecord] = []
        if self._approvals is not None:
            all_approvals = await self._approvals.list_by_run(run_id)
            for a in all_approvals:
                if a.state == "pending":
                    pending_approvals.append(
                        PendingApprovalRecord(
                            approval_id=a.id,
                            approval_kind=a.approval_kind,
                            summary=a.summary,
                            requested_at=a.requested_at.isoformat(),
                            expires_at=a.expires_at.isoformat()
                            if a.expires_at is not None
                            else None,
                        )
                    )

        # Manifest summary
        manifest_summary: ManifestSummaryModel | None = None
        if self._manifests is not None:
            manifest = await self._manifests.get(run_id)
            if manifest is not None:
                manifest_summary = ManifestSummaryModel(
                    run_id=run_id,
                    tool_policy_preset=manifest.tool_policy.preset,
                )
        plan_revision_models = [
            PlanRevisionRecordModel(
                seq=p.seq,
                run_id=p.run_id,
                version=p.version,
                artifact_ref=p.artifact_ref,
                diff_from_previous=p.diff_from_previous,
                rationale=p.rationale,
                timestamp=p.timestamp,
            )
            for p in plan_revisions
        ]

        # Convert to Pydantic models for API boundary
        return RunSnapshot(
            run_state=run_state,
            milestones=[
                MilestoneRecordModel(
                    seq=m.seq,
                    run_id=m.run_id,
                    phase=m.phase,
                    milestone=m.milestone,
                    description=m.description,
                    timestamp=m.timestamp,
                )
                for m in milestones
            ],
            artifacts=[
                ArtifactRecordModel(
                    seq=a.seq,
                    run_id=a.run_id,
                    artifact_kind=a.artifact_kind,
                    artifact_ref=a.artifact_ref,
                    label=a.label,
                    timestamp=a.timestamp,
                )
                for a in artifacts
            ],
            plan_revisions=plan_revision_models,
            pending_approvals=[
                PendingApprovalRecordModel(
                    approval_id=p.approval_id,
                    approval_kind=p.approval_kind,
                    summary=p.summary,
                    requested_at=p.requested_at,
                    expires_at=p.expires_at,
                )
                for p in pending_approvals
            ],
            latest_checkpoint_ref=latest_checkpoint_ref,
            manifest_summary=manifest_summary,
        )
