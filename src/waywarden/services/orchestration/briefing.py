"""EA briefing routine handler.

The briefing routine produces a dated briefing artifact by composing
intake and plan milestones through the orchestrated run lifecycle.
It reads inbox state and existing tasks to build a concise briefing
summary.

Canonical references:
    - RT-002 §Progress events
    - P4-3 #66 (orchestration service)
    - P5-1 #81 (metadata schema)
    - P5-2 #82 (asset registry)
    - P5-3 #83 (EAProfileView)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast

from waywarden.services.orchestration.milestones import (
    ALL_PHASES,
)


@dataclass(slots=True)
class InboxEntry:
    """An item in the EA inbox to be briefed."""

    subject: str
    body: str
    from_address: str
    received_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class BriefingState:
    """Current state of the briefing engine."""

    inbox_received: int = 0
    inbox_accepted: int = 0
    pending_tasks: int = 0
    artifacts_queued: int = 0


@dataclass(slots=True)
class BriefingResult:
    """Output from the briefing routine."""

    title: str
    timestamp: str
    state: BriefingState
    milestones: tuple[dict[str, Any], ...]
    artifact: dict[str, Any]


# ---------------------------------------------------------------------------
# Briefing handler
# ---------------------------------------------------------------------------


class EABriefingHandler:
    """Composes the intake -> plan milestones for the EA briefing routine.

    This handler is opinionated about what a briefing looks like:
    - Read all pending inbox items
    - Classify each (received/accepted)
    - Count pending tasks
    - Produce a dated briefing artifact
    - Emit run.progress milestones: intake(received, accepted) → plan(drafted, ready)

    In the real harness this would reach the inbox repository and
    task repository; here we accept inbox entries and pending task
    counts as arguments to keep the unit test simple.
    """

    def __init__(self) -> None:
        self._stderr: list[str] = []

    def run(
        self,
        inbox_entries: list[InboxEntry] | None = None,
        pending_tasks: int = 0,
        run_id: str = "ea-briefing-run",
    ) -> BriefingResult:
        """Execute the briefing routine.

        Args:
            inbox_entries: Items received from the inbox.
            pending_tasks: Number of tasks awaiting attention.
            run_id: Identifier for the run producing this briefing.

        Returns:
            A ``BriefingResult`` with the computed milestones and
            artifact.

        Raises:
            RuntimeError: When upstream data is unavailable.
        """
        inbox = inbox_entries or []
        state = BriefingState()
        state.inbox_received = len(inbox)

        # Classify items — everything with a non-empty subject is accepted
        for entry in inbox:
            if entry.subject.strip():
                state.inbox_accepted += 1
            else:
                self._stderr.append(f"inbox entry from {entry.from_address} has no subject")

        state.pending_tasks = pending_tasks
        state.artifacts_queued = 0

        # Build milestone stream
        milestones = [
            {"phase": "intake", "milestone": "received", "count": state.inbox_received},
            {"phase": "intake", "milestone": "accepted", "count": state.inbox_accepted},
            {"phase": "plan", "milestone": "drafted", "detail": "Briefing drafted"},
            {"phase": "plan", "milestone": "review", "detail": "Review pending"},
            {"phase": "plan", "milestone": "ready", "detail": "Briefing ready"},
        ]

        # Build artifact
        now = datetime.now(UTC)
        title = "EA Briefing — " + now.strftime("%Y-%m-%d")
        generated_at = now.isoformat()
        artifact = {
            "briefing_title": title,
            "items_received": state.inbox_received,
            "items_accepted": state.inbox_accepted,
            "pending_tasks": state.pending_tasks,
            "generated_at": generated_at,
            "errors": self._stderr,
        }

        return BriefingResult(
            title=title,
            timestamp=generated_at,
            state=state,
            milestones=cast(tuple[dict[str, Any], ...], tuple(milestones)),
            artifact=artifact,
        )


# ---------------------------------------------------------------------------
# Phase validation
# ---------------------------------------------------------------------------


def _validate_milestones(
    milestones: list[dict[str, Any]],
) -> None:
    """Validate that all milestones reference known phases."""
    valid = set(ALL_PHASES)
    for ms in milestones:
        phase = ms.get("phase")
        if phase not in valid:
            raise ValueError(f"milestone phase {phase!r} not in {sorted(valid)}")
