"""Orchestration service skeleton.

Drives a run through the ``intake -> plan -> execute -> review -> handoff``
sub-phases as a sequence of ``run.progress`` milestone events (RT-002).
Top-level ``Run.state`` values stay canonical per RT-002; the
orchestration service emits progress events alongside canonical state
transitions.

See ADR-0011 (adapter boundaries) and RT-002 (run event protocol).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from logging import getLogger
from typing import TYPE_CHECKING

from waywarden.domain.ids import RunEventId
from waywarden.domain.run import Run, RunState
from waywarden.domain.run_event import Actor, Causation, RunEvent
from waywarden.domain.token_usage import summary_artifact_ref
from waywarden.services.orchestration.milestones import is_valid_milestone

if TYPE_CHECKING:
    from waywarden.domain.repositories import RunEventRepository, RunRepository
    from waywarden.services.approval_engine import ApprovalEngine

logger = getLogger(__name__)


# Terminal events that suppress further run.progress emissions.
_TERMINAL_EVENTS: frozenset[str] = frozenset(["run.completed", "run.failed", "run.cancelled"])

# 7 canonical RT-002 run states — no invented states.
_VALID_RUN_STATES: frozenset[RunState] = frozenset(
    ["created", "planning", "executing", "waiting_approval", "completed", "failed", "cancelled"]
)


@dataclass(frozen=True, slots=True)
class OrchestrationService:
    """Drives a run through orchestration sub-phases.

    The service owns the phase machine lifecycle.  It writes canonical
    RT-002 lifecycle events (created, plan_ready, etc.) and emits
    ``run.progress`` milestones in the strict catalog from
    ``milestones.py``.

    Parameters
    ----------
    runs:
        Repository for ``Run`` persisted records.
    events:
        Append-only event log (RT-002).
    approvals:
        Approval engine for gating decisions.
    """

    runs: RunRepository = field(repr=False)
    events: RunEventRepository = field(repr=False)
    approvals: ApprovalEngine = field(repr=False)

    # -- public API ----------------------------------------------------------

    async def run(
        self,
        run: Run,
    ) -> Run:
        """Execute the full orchestration pipeline on *run*.

        Drives the canonical sub-phases:
        ``intake -> plan -> execute -> review -> handoff``.

        Parameters
        ----------
        run:
            The run to orchestrate.  Must be in ``created`` state.

        Returns
        -------
        The updated ``Run`` with terminal state.
        """
        if run.state != "created":
            raise ValueError(
                f"run must be in 'created' state to start orchestration, got {run.state!r}"
            )

        # Validate state space — only the 7 RT-002 states are allowed.
        assert run.state in _VALID_RUN_STATES, (
            f"State {run.state!r} is not in the 7 RT-002 run states"
        )

        next_run = await self._do_intake(run)
        next_run = await self._do_plan(next_run)
        next_run = await self._do_execute(next_run)
        next_run = await self._do_review(next_run)
        next_run = await self._do_handoff(next_run)

        return next_run

    # -- sub-phase implementations -------------------------------------------

    async def _do_intake(self, run: Run) -> Run:
        """intake phase: received → accepted."""
        now = datetime.now(UTC)

        # Emit intake.received
        await self._emit_progress(run, "intake", "received", now)

        # Emit intake.accepted
        await self._emit_progress(run, "intake", "accepted", now)

        # Transition: created → planning
        next_run = await self._update_state(run, "planning", now)
        return next_run

    async def _do_plan(self, run: Run) -> Run:
        """plan phase: drafted → approval_requested → ready."""
        now = datetime.now(UTC)

        # Emit plan.drafted
        await self._emit_progress(run, "plan", "drafted", now)

        # Emit plan.approval_requested (stub — approval engine integration)
        await self._emit_progress(run, "plan", "approval_requested", now)

        # Emit plan.ready (stub — simplified; no real approval gate in skeleton)
        await self._emit_progress(run, "plan", "ready", now)

        next_run = await self._update_state(run, "planning", now)
        return next_run

    async def _do_execute(self, run: Run) -> Run:
        """execute phase: tool_invoked → artifact_emitted → waiting_approval."""
        now = datetime.now(UTC)

        # Emit execute.tool_invoked
        await self._emit_progress(run, "execute", "tool_invoked", now)

        # Emit execute.artifact_emitted
        await self._emit_progress(run, "execute", "artifact_emitted", now)

        # Emit execute.waiting_approval
        await self._emit_progress(run, "execute", "waiting_approval", now)

        next_run = await self._update_state(run, "executing", now)
        return next_run

    async def _do_review(self, run: Run) -> Run:
        """review phase: findings_recorded."""
        now = datetime.now(UTC)

        await self._emit_progress(run, "review", "findings_recorded", now)

        next_run = await self._update_state(run, "planning", now)
        return next_run

    async def _do_handoff(self, run: Run) -> Run:
        """handoff phase: envelope_emitted → then terminal."""
        now = datetime.now(UTC)

        # Emit handoff.envelope_emitted (stub — P4-8 delegation)
        await self._emit_progress(run, "handoff", "envelope_emitted", now)

        # Emit terminal usage-summary artifact before completed
        await self._emit_usage_summary_artifact(run, now)

        # Emit run.completed event
        await self._emit_completed(run, now)

        # Terminal: completed
        next_run = await self._update_state(run, "completed", now)
        return next_run

    # -- helpers -------------------------------------------------------------

    async def _emit_progress(
        self,
        run: Run,
        phase: str,
        milestone: str,
        timestamp: datetime,
    ) -> None:
        """Emit a ``run.progress`` milestone event.

        Validates that the phase/milestone pair is in the catalog before
        persisting.
        """
        if not is_valid_milestone(phase, milestone):
            raise ValueError(
                f"progress event phase={phase!r}, milestone={milestone!r} "
                f"is not in the milestone catalog"
            )

        # Check terminal guard: no progress after terminal events.
        if self._is_terminal_run(run):
            raise RuntimeError(
                f"attempted to emit progress after run {run.id} reached "
                f"terminal state {run.state!r}"
            )

        last_seq = await self.events.latest_seq(str(run.id))
        event = RunEvent(
            id=RunEventId(f"evt-{run.id}-{phase}-{milestone}"),
            run_id=run.id,
            seq=last_seq + 1,
            type="run.progress",
            payload={
                "phase": phase,
                "milestone": milestone,
            },
            timestamp=timestamp,
            causation=Causation(
                event_id=None,
                action=f"{phase}.{milestone}",
                request_id=None,
            ),
            actor=Actor(kind="system", id=None, display=None),
        )

        await self.events.append(event)
        logger.debug("emitted run.progress(%s.%s) seq=%d", phase, milestone, event.seq)

    async def _emit_completed(self, run: Run, timestamp: datetime) -> None:
        """Emit the terminal ``run.completed`` event."""
        last_seq = await self.events.latest_seq(str(run.id))
        event = RunEvent(
            id=RunEventId(f"evt-{run.id}-completed"),
            run_id=run.id,
            seq=last_seq + 1,
            type="run.completed",
            payload={
                "outcome": "success",
            },
            timestamp=timestamp,
            causation=Causation(
                event_id=None,
                action="terminal_completion",
                request_id=None,
            ),
            actor=Actor(kind="system", id=None, display=None),
        )
        await self.events.append(event)

    async def _emit_usage_summary_artifact(
        self,
        run: Run,
        timestamp: datetime,
    ) -> None:
        """Emit the terminal ``run.artifact_created(kind=usage-summary)``."""
        last_seq = await self.events.latest_seq(str(run.id))
        artifact_ref = summary_artifact_ref(str(run.id))
        event = RunEvent(
            id=RunEventId(f"evt-{run.id}-usage-summary"),
            run_id=run.id,
            seq=last_seq + 1,
            type="run.artifact_created",
            payload={
                "artifact_ref": artifact_ref,
                "artifact_kind": "usage-summary",
                "label": "usage-summary",
            },
            timestamp=timestamp,
            causation=Causation(
                event_id=None,
                action="terminal_usage_summary",
                request_id=None,
            ),
            actor=Actor(kind="system", id=None, display=None),
        )
        await self.events.append(event)

    async def _update_state(
        self,
        run: Run,
        new_state: RunState,
        timestamp: datetime,
    ) -> Run:
        """Persist the run state transition."""
        assert new_state in _VALID_RUN_STATES, (
            f"State {new_state!r} is not in the 7 RT-002 run states"
        )
        updated = await self.runs.update_state(
            run_id=str(run.id),
            new_state=new_state,
            terminal_seq=None,
        )
        # Hydrate full record (skeleton: returns as-is since we don't have
        # a proper run repository implementation in tests).
        return updated

    def _is_terminal_run(self, run: Run) -> bool:
        """Return True if the run is in a terminal state."""
        return run.state in _VALID_RUN_STATES and run.state in {
            "completed",
            "failed",
            "cancelled",
        }
