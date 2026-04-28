"""RT-002 progress event helpers for team orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

from waywarden.domain.handoff import RunCorrelation
from waywarden.domain.ids import RunEventId, RunId
from waywarden.domain.run_event import Actor, Causation, RunEvent
from waywarden.domain.team import (
    Team,
    TeamMemberProgressStatus,
    TeamProgressMilestone,
    TeamProgressStatus,
)
from waywarden.services.orchestration.milestones import is_valid_milestone


def make_team_progress_event(
    *,
    run_id: RunId,
    team: Team,
    seq: int,
    milestone: TeamProgressMilestone,
    status: TeamProgressStatus,
    summary: str,
    member_statuses: dict[str, TeamMemberProgressStatus],
    correlation: RunCorrelation | None = None,
    now: datetime | None = None,
) -> RunEvent:
    """Build a catalog-valid team-level RT-002 ``run.progress`` event."""
    if not is_valid_milestone("handoff", milestone):
        raise ValueError(f"milestone not cataloged: phase='handoff' milestone={milestone!r}")

    clean_summary = summary.strip()
    if not clean_summary:
        raise ValueError("summary must not be blank")

    member_ids = set(team.member_ids)
    unknown_members = sorted(set(member_statuses) - member_ids)
    if unknown_members:
        raise ValueError(f"unknown team member statuses: {unknown_members}")
    missing_members = sorted(member_ids - set(member_statuses))
    if missing_members:
        raise ValueError(f"missing team member statuses: {missing_members}")

    normalized_statuses = {member_id: member_statuses[member_id] for member_id in team.member_ids}
    timestamp = now or datetime.now(UTC)
    payload: dict[str, object] = {
        "phase": "handoff",
        "milestone": milestone,
        "team_id": str(team.id),
        "dispatcher_id": str(team.dispatcher.id),
        "specialist_ids": tuple(str(agent.id) for agent in team.specialists),
        "status": status,
        "summary": clean_summary,
        "member_statuses": normalized_statuses,
    }
    if correlation is not None:
        payload.update(correlation.as_payload())

    return RunEvent(
        id=RunEventId(f"evt-{run_id}-{team.id}-{milestone}-{uuid4().hex}"),
        run_id=run_id,
        seq=seq,
        type="run.progress",
        payload=payload,
        timestamp=timestamp,
        causation=Causation(
            event_id=None,
            action=cast(str, milestone),
            request_id=str(team.id),
        ),
        actor=Actor(kind="system", id=str(team.id), display=str(team.id)),
    )


__all__ = ["make_team_progress_event"]
