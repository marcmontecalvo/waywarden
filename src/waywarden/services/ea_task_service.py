"""EA-facing task service wired through durable repositories and ApprovalEngine.

This service provides an **Approver** primitive that EA routines can use
to create tasks, request approvals, and transition tasks.  It is fully
backed by ``TaskRepository``, the ``ApprovalEngine``, and
``RunEventRepository`` — no in-memory state shortcuts.

Approval paths route through the P3 approval engine and emit catalog-
valid RT-002 events.  No new event types are introduced.

Canonical references:
    - ADR 0005 (approval model)
    - RT-002 §Approval decision event mapping
    - P5-3 #83 (EAProfileView)
    - P2-4 #39 (task domain)
    - P3 #58 (approval engine)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from logging import getLogger
from typing import TYPE_CHECKING
from uuid import uuid4

from waywarden.domain.ids import RunEventId, RunId, SessionId, TaskId
from waywarden.domain.run_event import Actor, Causation, RunEvent
from waywarden.services.orchestration.milestones import is_valid_milestone

if TYPE_CHECKING:
    from waywarden.domain.repositories import RunEventRepository, TaskRepository
    from waywarden.domain.task import Task
    from waywarden.services.approval_engine import ApprovalEngine
    from waywarden.services.approval_types import ApprovalDecision

logger = getLogger(__name__)


# ---------------------------------------------------------------------------
# DTO types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateTaskRequest:
    """Input for creating a task via the EA task service."""

    session_id: str
    title: str
    objective: str
    acceptance_criteria: tuple[str, ...] = ()
    run_id: str | None = None


@dataclass(frozen=True, slots=True)
class TransitionTaskRequest:
    """Input for transitioning a task."""

    task_id: str
    state: str
    run_id: str | None = None


@dataclass(frozen=True, slots=True)
class RequestApprovalRequest:
    """Input for requesting an approval checkpoint."""

    task_id: str
    run_id: str = ""
    approval_kind: str = "ea_checkpoint"
    approval_context: dict[str, object] | None = None
    summary: str = ""


@dataclass(frozen=True, slots=True)
class ApprovalDecisionRequest:
    """Input for an approval decision."""

    task_id: str
    decision: ApprovalDecision
    run_id: str | None = None
    approval_kind: str = "ea_checkpoint"


# ---------------------------------------------------------------------------
# TaskState helper — kept local so callers import from the service layer.
# ---------------------------------------------------------------------------

TaskState = str  # Aliased to the domain TaskState values


async def _require_task(
    task_repo: TaskRepository,
    task_id: str,
    *,
    method: str = "EATaskService",
) -> Task:
    """Load and return a task, raising ``KeyError`` if missing."""
    task = await task_repo.get(task_id)
    if task is None:
        raise KeyError(f"{method}: task {task_id!r} not found")
    return task


# ---------------------------------------------------------------------------
# EATaskService — repository-backed
# ---------------------------------------------------------------------------


class EATaskService:
    """EA-facing task service backed by durable repositories.

    Parameters
    ----------
    task_repo:
        Repository for :class:`~waywarden.domain.task.Task` records.
    approval_engine:
        The P3 ``ApprovalEngine`` that routes approval decisions
        through the real ``ApprovalRepository`` and ``RunEventRepository``.
    events:
        Append-only event log (RT-002) shared with the rest of the runtime.
    """

    def __init__(
        self,
        task_repo: TaskRepository,
        approval_engine: ApprovalEngine,
        events: RunEventRepository,
    ) -> None:
        self._task_repo = task_repo
        self._approval_engine = approval_engine
        self._events = events

    # ---- task CRUD ----

    async def create_task(self, req: CreateTaskRequest) -> dict[str, object]:
        """Create a new task, persist it, and emit ``run.progress``."""
        run_id = req.run_id or f"ea-{req.session_id}"
        ts = datetime.now(UTC)
        task_id = f"task-{req.session_id}"
        # De-duplicate task id in repo by appending a counter if needed
        existing = await self._task_repo.get(task_id)
        if existing is not None:
            counter = 1
            while True:
                candidate = f"{task_id}-{counter}"
                if not await self._task_repo.get(candidate):
                    task_id = candidate
                    break
                counter += 1
        # Import the real domain class at runtime to avoid circular imports
        from waywarden.domain.task import Task as DomainTask

        domain_task = DomainTask(
            id=TaskId(task_id),
            session_id=SessionId(req.session_id),
            title=req.title,
            objective=req.objective,
            state="draft",
            created_at=ts,
            updated_at=ts,
        )
        await self._task_repo.save(domain_task)
        await self._emit_progress(run_id, task_id, _task_created_payload(task_id))
        return {
            "id": task_id,
            "session_id": req.session_id,
            "title": req.title,
            "objective": req.objective,
            "state": "draft",
        }

    # ---- transitions ----

    async def transition_task(self, req: TransitionTaskRequest) -> dict[str, object]:
        """Transition a persistent task to a new state."""
        task = await _require_task(self._task_repo, req.task_id, method="transition_task")
        allowed_transitions: dict[str, tuple[str, ...]] = {
            "draft": ("planning",),
            "planning": ("executing", "cancelled"),
            "executing": ("waiting_approval", "failed", "completed"),
            "waiting_approval": ("planning", "cancelled", "failed"),
            "completed": (),
            "failed": (),
            "cancelled": (),
        }
        valid_next = allowed_transitions.get(task.state, ())
        if req.state not in valid_next:
            raise ValueError(f"cannot transition {task.state!r} -> {req.state!r}")
        from waywarden.domain.task import Task as DomainTask

        updated = DomainTask(
            id=task.id,
            session_id=task.session_id,
            title=task.title,
            objective=task.objective,
            state=req.state,  # type: ignore[arg-type]
            created_at=task.created_at,
            updated_at=datetime.now(UTC),
        )
        await self._task_repo.save(updated)
        run_id = req.run_id or _default_run_id(task.session_id)
        await self._emit_progress(run_id, str(task.id), _task_transition_payload(req.state))
        return {
            "id": str(task.id),
            "state": req.state,
            "session_id": task.session_id,
        }

    # ---- approvals ----

    async def request_approval(self, req: RequestApprovalRequest) -> dict[str, object]:
        """Create a domain task transition + approval request via ApprovalEngine.

        Transitions the backing task to ``waiting_approval`` and delegates
        the approval checkpoint to the ``ApprovalEngine`` which emits
        ``run.approval_waiting`` through the durable event repository.
        """
        task = await _require_task(self._task_repo, req.task_id, method="request_approval")
        if task.state != "executing":
            raise ValueError(
                f"task {req.task_id!r} is in state {task.state!r}, expected 'executing'"
            )
        # Transition to waiting_approval
        from waywarden.domain.task import Task as DomainTask

        updated = DomainTask(
            id=task.id,
            session_id=task.session_id,
            title=task.title,
            objective=task.objective,
            state="waiting_approval",
            created_at=task.created_at,
            updated_at=datetime.now(UTC),
        )
        await self._task_repo.save(updated)

        # Delegate approval creation to ApprovalEngine
        # We inject task_id into the approval kind so the round-trip is deterministic.
        enriched_kind = f"{req.approval_kind}-{req.task_id}"
        approval_summary = req.summary or f"Approval checkpoint for {task.title}"
        run_id = req.run_id or _default_run_id(task.session_id)
        approval = await self._approval_engine.request(
            run_id=run_id,
            approval_kind=enriched_kind,
            summary=approval_summary,
            checkpoint_ref=req.task_id,
        )
        await self._events.append(
            RunEvent(
                id=RunEventId(f"evt-{req.task_id}-approval-annotate-{uuid4().hex}"),
                run_id=RunId(run_id),
                seq=(await self._events.latest_seq(run_id)) + 1,
                type="run.progress",
                payload={
                    "phase": "plan",
                    "milestone": "approval_requested",
                    "approval_id": str(approval.id),
                    "task_id": req.task_id,
                    "ea_event": "approval_requested",
                },
                timestamp=datetime.now(UTC),
                causation=Causation(
                    event_id=None, action="request_approval", request_id=str(approval.id)
                ),
                actor=Actor(kind="system", id=None, display=None),
            )
        )
        return {
            "task_id": req.task_id,
            "approval_id": str(approval.id),
            "approval_kind": req.approval_kind,
            "state": "waiting_approval",
        }

    async def resolve_approval(self, req: ApprovalDecisionRequest) -> dict[str, object]:
        """Resolve an approval through ApprovalEngine and propagate the result.

        The ``ApprovalEngine`` handles the domain validation and emits the
        mapped RT-002 event.  We annotate the transition in our event log.
        """
        task = await _require_task(self._task_repo, req.task_id, method="resolve_approval")

        run_id = req.run_id or _default_run_id(task.session_id)
        approval_id = _approval_id(
            run_id=run_id,
            approval_kind=req.approval_kind,
            task_id=req.task_id,
        )
        approval = await self._approval_engine.approvals.get(approval_id)
        if approval is None:
            raise KeyError(f"approval {approval_id!r} not found")
        if approval.state != "pending":
            from waywarden.services.approval_types import ApprovalAlreadyResolvedError

            raise ApprovalAlreadyResolvedError(approval_id=str(approval.id))

        # Route through ApprovalEngine (stores updated approval + emits RT-002)
        _emitted = await self._approval_engine.resolve(approval_id, req.decision)

        # Map the engine event back to an EA-friendly response.
        # Terminal deny/timeout transitions are applied here.
        # Pre-approved transitions (e.g. granted→planning) are left for
        # the caller to compose via transition_task.
        resolution_map: dict[str, str] = {
            "granted": "granted",
            "denied_abandon": "denied_abandon",
            "denied_alternate_path": "denied_alternate_path",
            "timeout": "timeout",
        }
        ea_state = resolution_map.get(req.decision.decision, "resolved")

        from waywarden.domain.task import Task as DomainTask

        # Only terminal transitions are applied here.
        # Non-terminal: granted/denied_alternate_path → planning is deferred
        # to the caller via explicit transition_task.
        terminal_transitions: dict[str, str] = {
            "denied": "cancelled",
            "timeout": "failed",
        }
        post_state = terminal_transitions.get(req.decision.decision, task.state)
        if post_state != task.state:
            updated = DomainTask(
                id=task.id,
                session_id=task.session_id,
                title=task.title,
                objective=task.objective,
                state=post_state,  # type: ignore[arg-type]
                created_at=task.created_at,
                updated_at=datetime.now(UTC),
            )
            await self._task_repo.save(updated)

        return {
            "task_id": req.task_id,
            "approval_id": str(approval.id),
            "state": ea_state,
            "resolved": True,
        }

    # ---- internal helpers ----

    async def _emit_progress(
        self,
        run_id: str,
        task_id: str,
        payload: dict[str, object],
    ) -> None:
        """Append a ``run.progress`` event to the run event log.

        The caller must include a catalog-valid ``phase`` and
        ``milestone`` in *payload* to satisfy RT-002.
        """
        phase = payload.get("phase")
        milestone = payload.get("milestone")
        if not isinstance(phase, str) or not isinstance(milestone, str):
            raise ValueError("run.progress payload requires string phase and milestone")
        if not is_valid_milestone(phase, milestone):
            raise ValueError(f"unknown run.progress milestone {phase}.{milestone}")
        await self._events.append(
            RunEvent(
                id=RunEventId(f"evt-{task_id}-progress-{uuid4().hex}"),
                run_id=RunId(run_id),
                seq=(await self._events.latest_seq(run_id)) + 1,
                type="run.progress",
                payload=payload,
                timestamp=datetime.now(UTC),
                causation=Causation(event_id=None, action="ea_task", request_id=task_id),
                actor=Actor(kind="system", id=None, display=None),
            )
        )


def _default_run_id(session_id: str) -> str:
    return f"ea-{session_id}"


def _approval_id(*, run_id: str, approval_kind: str, task_id: str) -> str:
    enriched_kind = f"{approval_kind}-{task_id}"
    return f"approval-{run_id}-{enriched_kind}"


def _task_created_payload(task_id: str) -> dict[str, object]:
    return {
        "phase": "intake",
        "milestone": "accepted",
        "task_id": task_id,
        "ea_event": "task_created",
    }


def _task_transition_payload(state: str) -> dict[str, object]:
    phase, milestone = _catalog_pair_for_state(state)
    return {
        "phase": phase,
        "milestone": milestone,
        "to_state": state,
        "ea_event": "task_transitioned",
    }


def _catalog_pair_for_state(state: str) -> tuple[str, str]:
    if state == "planning":
        return "plan", "drafted"
    if state == "executing":
        return "plan", "ready"
    if state == "waiting_approval":
        return "execute", "waiting_approval"
    if state == "completed":
        return "execute", "artifact_emitted"
    if state in {"failed", "cancelled"}:
        return "review", "findings_recorded"
    return "intake", "accepted"
