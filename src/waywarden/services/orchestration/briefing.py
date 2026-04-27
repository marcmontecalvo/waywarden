"""EA briefing routine handler.

The briefing routine produces a dated briefing artifact by composing
intake and plan milestones through the orchestrated run lifecycle.
It reads inbox state and existing tasks to build a concise briefing
summary.

When attached to a ``RunEventRepository`` it emits catalog-valid
``run.progress`` milestones and a ``run.artifact_created`` event for
the generated briefing document.

Canonical references:
    - RT-002 §Progress events
    - RT-002 §Artifact events
    - P4-3 #66 (orchestration service)
    - P5-1 #81 (metadata schema)
    - P5-2 #82 (asset registry)
    - P5-3 #83 (EAProfileView)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from logging import getLogger
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

from waywarden.domain.ids import RunEventId, RunId
from waywarden.domain.run_event import Actor, Causation, RunEvent
from waywarden.services.orchestration.milestones import (
    ALL_PHASES,
    is_valid_milestone,
)

if TYPE_CHECKING:
    from waywarden.domain.repositories import RunEventRepository

logger = getLogger(__name__)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


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

    When constructed with an ``event_repo`` it emits catalog-valid
    ``run.progress`` milestones and a durable ``run.artifact_created``
    event as part of its run lifecycle.

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

    def __init__(
        self,
        event_repo: RunEventRepository | None = None,
        *,
        events: list[Any] | None = None,
    ) -> None:
        self._stderr: list[str] = []
        self._event_repo = event_repo
        self._snapshot = events

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

        Returns:
            A ``BriefingResult`` with the computed milestones and
            artifact.
        """
        result, now = self._build_result(inbox_entries=inbox_entries, pending_tasks=pending_tasks)

        # Synchronous compatibility path for unit tests and non-async callers.
        # Async runtimes must call ``run_async`` so durable event writes are awaited.
        if self._event_repo is not None:
            import asyncio

            try:
                asyncio.get_running_loop()
            except RuntimeError:
                asyncio.run(self._emit_events(result, now, run_id=run_id))
            else:
                raise RuntimeError(
                    "EABriefingHandler.run() cannot persist events in async runtime; "
                    "use run_async()"
                )

        return result

    async def run_async(
        self,
        inbox_entries: list[InboxEntry] | None = None,
        pending_tasks: int = 0,
        run_id: str = "ea-briefing-run",
    ) -> BriefingResult:
        """Execute briefing and await durable event persistence."""
        result, now = self._build_result(inbox_entries=inbox_entries, pending_tasks=pending_tasks)
        if self._event_repo is not None:
            await self._emit_events(result, now, run_id=run_id)
        return result

    def _build_result(
        self,
        *,
        inbox_entries: list[InboxEntry] | None,
        pending_tasks: int,
    ) -> tuple[BriefingResult, datetime]:
        inbox = inbox_entries or []
        state = BriefingState()
        state.inbox_received = len(inbox)

        for entry in inbox:
            if entry.subject.strip():
                state.inbox_accepted += 1
            else:
                self._stderr.append(f"inbox entry from {entry.from_address} has no subject")

        state.pending_tasks = pending_tasks
        state.artifacts_queued = 0

        # Build milestone stream
        milestones: list[dict[str, Any]] = [
            {
                "phase": "intake",
                "milestone": "received",
                "count": state.inbox_received,
            },
            {
                "phase": "intake",
                "milestone": "accepted",
                "count": state.inbox_accepted,
            },
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

        result = BriefingResult(
            title=title,
            timestamp=generated_at,
            state=state,
            milestones=cast(tuple[dict[str, Any], ...], tuple(milestones)),
            artifact=artifact,
        )
        return result, now

    # -- internal helpers ---------------------------------------------------

    async def _emit_run(self, event: Any) -> None:
        """Append an event to the durable repo or capture list."""
        if self._event_repo is not None:
            await self._event_repo.append(event)
        # Snapshot capture for tests.
        if self._snapshot is not None:
            self._snapshot.append(event)

    async def _emit_events(
        self,
        result: BriefingResult,
        timestamp: datetime,
        *,
        run_id: str,
    ) -> None:
        await self._emit_milestones(timestamp, milestones=list(result.milestones), run_id=run_id)
        await self._emit_artifact(
            run_id=run_id,
            art_ref=f"briefing-{result.timestamp}",
            artifact_kind="briefing",
            label="briefing",
        )

    async def _emit_milestones(
        self,
        timestamp: datetime,
        milestones: list[dict[str, Any]],
        *,
        run_id: str,
    ) -> None:
        """Emit catalog-valid ``run.progress`` milestones."""
        for ms in milestones:
            phase = ms.get("phase")
            milestone = ms.get("milestone")
            if phase is None or milestone is None:
                continue
            if not is_valid_milestone(phase, milestone):
                logger.warning("milestone %s.%s not in catalog", phase, milestone)
                continue
            event = RunEvent(
                id=RunEventId(f"evt-{run_id}-briefing-{phase}-{milestone}-{uuid4().hex}"),
                run_id=RunId(run_id),
                seq=(await self._event_repo.latest_seq(run_id)) + 1 if self._event_repo else 1,
                type="run.progress",
                payload=MappingProxyType(dict(ms)),
                timestamp=timestamp,
                causation=Causation(
                    event_id=None,
                    action=f"briefing.{phase}.{milestone}",
                    request_id=None,
                ),
                actor=Actor(kind="system", id=None, display=None),
            )
            await self._emit_run(event)

    async def _emit_artifact(
        self,
        *,
        run_id: str,
        art_ref: str,
        artifact_kind: str,
        label: str,
    ) -> None:
        """Emit ``run.artifact_created`` for the briefing."""
        event = RunEvent(
            id=RunEventId(f"evt-{run_id}-briefing-artifact-{uuid4().hex}"),
            run_id=RunId(run_id),
            seq=(await self._event_repo.latest_seq(run_id)) + 1 if self._event_repo else 1,
            type="run.artifact_created",
            payload=MappingProxyType(
                {
                    "artifact_ref": art_ref,
                    "artifact_kind": artifact_kind,
                    "label": label,
                }
            ),
            timestamp=datetime.now(UTC),
            causation=Causation(
                event_id=None,
                action="briefing_artifact_created",
                request_id=None,
            ),
            actor=Actor(kind="system", id=None, display=None),
        )
        await self._emit_run(event)


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
