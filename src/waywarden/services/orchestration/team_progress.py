"""RT-002 progress event helpers for team orchestration."""

from __future__ import annotations

from collections.abc import Mapping
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
    member_run_ids: Mapping[str, str] | None = None,
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
    if member_run_ids is not None:
        unknown_run_ids = sorted(set(member_run_ids) - member_ids)
        if unknown_run_ids:
            raise ValueError(f"unknown team member run ids: {unknown_run_ids}")
        missing_run_ids = sorted(member_ids - set(member_run_ids))
        if missing_run_ids:
            raise ValueError(f"missing team member run ids: {missing_run_ids}")
        for member_id, member_run_id in member_run_ids.items():
            if not str(member_run_id).strip():
                raise ValueError(f"member run id must not be blank for {member_id!r}")

    normalized_statuses = {member_id: member_statuses[member_id] for member_id in team.member_ids}
    milestone_ref = f"handoff.{milestone}"
    agent_progress: list[dict[str, object]] = []
    for member_id in team.member_ids:
        entry: dict[str, object] = {
            "agent_id": member_id,
            "run_id": (member_run_ids[member_id] if member_run_ids is not None else str(run_id)),
            "status": normalized_statuses[member_id],
            "milestone_ref": milestone_ref,
        }
        if correlation is not None:
            entry["parent_run_id"] = str(correlation.parent_run_id)
        agent_progress.append(entry)
    timestamp = now or datetime.now(UTC)
    payload: dict[str, object] = {
        "phase": "handoff",
        "milestone": milestone,
        "milestone_ref": milestone_ref,
        "run_id": str(run_id),
        "team_id": str(team.id),
        "dispatcher_id": str(team.dispatcher.id),
        "specialist_ids": tuple(str(agent.id) for agent in team.specialists),
        "status": status,
        "summary": clean_summary,
        "member_statuses": normalized_statuses,
        "agent_progress": tuple(agent_progress),
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
