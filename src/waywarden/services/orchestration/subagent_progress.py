"""RT-002 progress event helpers for sub-agent orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

from waywarden.domain.handoff import RunCorrelation
from waywarden.domain.ids import RunEventId, RunId
from waywarden.domain.run_event import Actor, Causation, RunEvent
from waywarden.domain.subagent import (
    SubAgent,
    SubAgentProgressMilestone,
    SubAgentProgressStatus,
)
from waywarden.services.orchestration.milestones import is_valid_milestone


def make_sub_agent_progress_event(
    *,
    run_id: RunId,
    sub_agent: SubAgent,
    seq: int,
    milestone: SubAgentProgressMilestone,
    status: SubAgentProgressStatus,
    summary: str,
    correlation: RunCorrelation | None = None,
    now: datetime | None = None,
) -> RunEvent:
    """Build a catalog-valid RT-002 ``run.progress`` event for a sub-agent."""
    if not is_valid_milestone("handoff", milestone):
        raise ValueError(f"milestone not cataloged: phase='handoff' milestone={milestone!r}")

    timestamp = now or datetime.now(UTC)
    clean_summary = summary.strip()
    if not clean_summary:
        raise ValueError("summary must not be blank")
    payload: dict[str, object] = {
        "phase": "handoff",
        "milestone": milestone,
        "milestone_ref": f"handoff.{milestone}",
        "run_id": str(run_id),
        "agent_id": str(sub_agent.id),
        "sub_agent_id": str(sub_agent.id),
        "role": sub_agent.role.name,
        "status": status,
        "summary": clean_summary,
    }
    if correlation is not None:
        payload.update(correlation.as_payload())

    return RunEvent(
        id=RunEventId(f"evt-{run_id}-{sub_agent.id}-{milestone}-{uuid4().hex}"),
        run_id=run_id,
        seq=seq,
        type="run.progress",
        payload=payload,
        timestamp=timestamp,
        causation=Causation(
            event_id=None,
            action=cast(str, milestone),
            request_id=str(sub_agent.id),
        ),
        actor=Actor(kind="system", id=str(sub_agent.id), display=sub_agent.role.name),
    )


__all__ = ["make_sub_agent_progress_event"]
