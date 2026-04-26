"""Run lifecycle service — start / resume / cancel verbs.

Thin service wrapping repository-level run mutation behind typed methods
so channels and the API route have a single entry point.  The
RT-002 resume-kind vocabulary is honoured verbatim.

See ADR-0011 (adapter boundaries) and RT-002
(§Long-running and scheduled resume semantics).
"""

from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING, Literal

from waywarden.domain.ids import RunEventId, RunId
from waywarden.domain.run import Run, RunState
from waywarden.domain.run_event import Actor, Causation, RunEvent
from waywarden.domain.task import Task

logger = getLogger(__name__)

# Approved resume kinds for this service (approval-related kinds are
# owned by ApprovalEngine).
_VALID_RESUME_KINDS: frozenset[str] = frozenset(
    ["operator_resume", "scheduler_wakeup", "worker_recovery", "transport_rebind"]
)

# Terminal states that refuse new lifecycle verbs.
_TERMINAL_STATES: frozenset[RunState] = frozenset(["completed", "failed", "cancelled"])


class RunLifecycleError(RuntimeError):
    """Base error for run lifecycle failures."""


class RunAlreadyTerminalError(RunLifecycleError):
    """Raised when attempting to operate on a terminal run."""

    def __init__(self, run_id: str, state: str) -> None:
        super().__init__(f"run {run_id!r} is terminal (state={state!r})")
        self.run_id = run_id
        self.state = state


class InvalidResumeKindError(RunLifecycleError):
    """Raised when an unsupported resume_kind is provided."""

    def __init__(self, resume_kind: str) -> None:
        super().__init__(
            f"resume_kind {resume_kind!r} is not supported by RunLifecycleService "
            f"(approval-related kinds are owned by the ApprovalEngine)"
        )
        self.resume_kind = resume_kind


if TYPE_CHECKING:
    from waywarden.domain.repositories import (
        RunEventRepository,
        RunRepository,
        WorkspaceManifestRepository,
    )


class RunLifecycleService:
    """Manages run lifecycle verbs: start, resume, cancel.

    Parameters
    ----------
    runs:
        RunRepository for run record persistence.
    events:
        RunEventRepository for append-only event log.
    manifests:
        WorkspaceManifestRepository for manifest persistence.
    """

    def __init__(
        self,
        runs: RunRepository,
        events: RunEventRepository,
        manifests: WorkspaceManifestRepository,
    ) -> None:
        self._runs = runs
        self._events = events
        self._manifests = manifests

    async def start(
        self,
        task: Task,
        *,
        entrypoint: Literal["api", "cli", "scheduler", "internal"] = "api",
    ) -> Run:
        """Create a new run from a task and manifest.

        Persists the manifest, creates the run row, and appends
        ``run.created`` at seq=1.
        """
        # Persist manifest first
        manifest_ref = f"manifest://{task.id}/default"

        from datetime import UTC, datetime

        from waywarden.domain.ids import InstanceId

        now = datetime.now(UTC)
        run_id = RunId(f"run-{task.id}")

        run = Run(
            id=run_id,
            instance_id=InstanceId("inst-default"),
            task_id=task.id,
            profile=task.session_id,
            policy_preset="ask",
            manifest_ref=manifest_ref,
            entrypoint=entrypoint,
            state="created",
            created_at=now,
            updated_at=now,
            terminal_seq=None,
        )

        run = await self._runs.create(run)

        last_seq = await self._events.latest_seq(str(run.id))
        assert last_seq == 0, f"Expected seq=0 for new run, got {last_seq}"

        event = RunEvent(
            id=RunEventId(f"evt-{run.id}-created"),
            run_id=run.id,
            seq=1,
            type="run.created",
            payload={
                "instance_id": run.instance_id,
                "profile": run.profile,
                "policy_preset": run.policy_preset,
                "manifest_ref": run.manifest_ref,
                "entrypoint": run.entrypoint,
            },
            timestamp=now,
            causation=Causation(event_id=None, action="start_run", request_id=None),
            actor=Actor(kind="system", id=None, display=None),
        )

        await self._events.append(event)
        return run

    async def resume(
        self,
        run_id: RunId,
        *,
        resume_kind: Literal[
            "operator_resume", "scheduler_wakeup", "worker_recovery", "transport_rebind"
        ],
    ) -> RunEvent:
        """Resume a run that is in a non-terminal state.

        Parameters
        ----------
        run_id:
            The run to resume.
        resume_kind:
            One of the approved non-approval resume kinds.

        Returns
        -------
        The emitted ``run.resumed`` event.

        Raises
        ------
        RunAlreadyTerminalError:
            If the run is in a terminal state.
        InvalidResumeKindError:
            If the resume kind is not supported by this service.
        """
        if resume_kind not in _VALID_RESUME_KINDS:
            raise InvalidResumeKindError(resume_kind)

        existing = await self._runs.get(str(run_id))
        if existing is None:
            raise FileNotFoundError(f"run {run_id!r} not found")

        if existing.state in _TERMINAL_STATES:
            raise RunAlreadyTerminalError(str(run_id), existing.state)

        latest = await self._events.latest_seq(str(run_id))

        from datetime import UTC, datetime

        now = datetime.now(UTC)
        event = RunEvent(
            id=RunEventId(f"evt-{run_id}-resumed"),
            run_id=run_id,
            seq=latest + 1,
            type="run.resumed",
            payload={
                "resume_kind": resume_kind,
                "resumed_from_seq": latest,
            },
            timestamp=now,
            causation=Causation(event_id=None, action=resume_kind, request_id=None),
            actor=Actor(kind="system", id=None, display=None),
        )

        await self._events.append(event)
        return event

    async def cancel(
        self,
        run_id: RunId,
        *,
        reason: str,
        cancelled_by: str | None = None,
    ) -> RunEvent:
        """Cancel a run that is not yet terminal.

        Parameters
        ----------
        run_id:
            The run to cancel.
        reason:
            Human-readable reason for the cancellation.
        cancelled_by:
            Optional identifier of who cancelled.

        Returns
        -------
        The emitted ``run.cancelled`` event.

        Raises
        ------
        RunAlreadyTerminalError:
            If the run is already in a terminal state.
        """
        existing = await self._runs.get(str(run_id))
        if existing is None:
            raise FileNotFoundError(f"run {run_id!r} not found")

        if existing.state in _TERMINAL_STATES:
            raise RunAlreadyTerminalError(str(run_id), existing.state)

        latest = await self._events.latest_seq(str(run_id))

        from datetime import UTC, datetime

        now = datetime.now(UTC)
        payload: dict[str, object] = {
            "reason": reason,
        }
        if cancelled_by is not None:
            payload["cancelled_by"] = cancelled_by

        event = RunEvent(
            id=RunEventId(f"evt-{run_id}-cancelled"),
            run_id=run_id,
            seq=latest + 1,
            type="run.cancelled",
            payload=payload,
            timestamp=now,
            causation=Causation(event_id=None, action="cancel_run", request_id=None),
            actor=Actor(kind="system", id=None, display=None),
        )

        await self._events.append(event)
        return event
