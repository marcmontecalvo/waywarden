"""GET /runs/{run_id}/view — Visibility surface for run progress.

This module is the API boundary of the visibility layer.  It delegates to
``VisibilityService.snapshot()`` which reads exclusively from the RT-002
event log.  No events are emitted by this route.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException

from waywarden.domain.repositories import (
    RunEventRepository,
    RunRepository,
    WorkspaceManifestRepository,
)
from waywarden.services.visibility import RunSnapshot, VisibilityService

if TYPE_CHECKING:
    from waywarden.domain.repositories import ApprovalRepository

router = APIRouter(tags=["run-view"])

# -- Dependency injection (set in test harness or app startup) ---------------

_event_repo: RunEventRepository | None = None
_run_repo: RunRepository | None = None
_manifest_repo: WorkspaceManifestRepository | None = None
_approval_repo: ApprovalRepository | None = None


def _get_events() -> RunEventRepository | None:
    return _event_repo


def _get_runs() -> RunRepository | None:
    return _run_repo


def _get_manifests() -> WorkspaceManifestRepository | None:
    return _manifest_repo


def _get_approvals() -> ApprovalRepository | None:
    return _approval_repo


@router.get(
    "/runs/{run_id}/view",
    summary="Run visibility snapshot",
    response_model=RunSnapshot,
)
async def get_run_view(
    run_id: str,
) -> dict[str, Any]:
    """Return a JSON snapshot of a run's current state.

    Response contains:
    - ``run_state`` — current RT-002 state
    - ``milestones`` — every ``run.progress`` event in seq order
    - ``artifacts`` — every ``run.artifact_created`` event
    - ``pending_approvals`` — pending approvals from the P3 approval engine
    - ``latest_checkpoint_ref`` — always ``null`` for P4
    - ``manifest_summary`` — redacted RT-001 overview

    Returns 404 if the run is unknown.
    """
    events_repo = _get_events()
    runs_repo = _get_runs()
    manifests_repo = _get_manifests()
    approval_repo = _get_approvals()

    if events_repo is None:
        raise HTTPException(status_code=503, detail="event repository not configured")

    service = VisibilityService(
        events=events_repo,
        runs=runs_repo,
        manifests=manifests_repo,
        approvals=approval_repo,
    )

    # Check if the run exists — must do so before calling snapshot to return 404
    if runs_repo is not None:
        run = await runs_repo.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    # If no run repo, still allow snapshot (events repo alone) — 404 handled by events

    snapshot = await service.snapshot(run_id)

    # If no runs_repo and no events found, treat as 404
    if runs_repo is None:
        latest = await events_repo.latest_seq(run_id)
        if latest == 0:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    return snapshot.model_dump()
