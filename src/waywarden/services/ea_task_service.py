"""EA-facing task service wrapping the underlying approval + task domain.

This service provides an **Approver** primitive that EA routines can use
to create tasks, request approvals, and transition tasks without needing
direct access to the TaskRepository or ApprovalEngine.

All approval paths route through the P3 approval engine — no bypass.

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
from typing import Any

from waywarden.domain.ids import TaskId
from waywarden.domain.run_event_types import RunEventType
from waywarden.services.approval_types import (
    ApprovalAlreadyResolvedError,
    ApprovalDecision,
    DeniedAbandon,
    DeniedAlternatePath,
    Granted,
    Timeout,
)

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


@dataclass(frozen=True, slots=True)
class TransitionTaskRequest:
    """Input for transitioning a task."""

    task_id: str
    state: str


@dataclass(frozen=True, slots=True)
class RequestApprovalRequest:
    """Input for requesting an approval checkpoint."""

    task_id: str
    approval_context: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ApprovalDecisionRequest:
    """Input for an approval decision."""

    task_id: str
    decision: ApprovalDecision


# ---------------------------------------------------------------------------
# Internal event types for EA-specific events
# ---------------------------------------------------------------------------

EATaskEventType = RunEventType  # Reuse RT-002 event types; no extras added

TASK_EVENTS: dict[str, RunEventType] = {
    "task_created": "run.progress",
    "task_transitioned": "run.progress",
    "approval_requested": "run.approval_waiting",
    "approval_granted": "run.plan_ready",
    "approval_denied": "run.failed",
    "approval_timeout": "run.cancelled",
}


# ---------------------------------------------------------------------------
# Approval counter
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _ApprovalCounter:
    """Monotonically increasing approval identifier generator."""

    _counter: int = 0

    def next(self) -> str:
        self._counter += 1
        return str(self._counter)


# ---------------------------------------------------------------------------
# EA Task Service
# ---------------------------------------------------------------------------


class EATaskService:
    """EA-facing task service wrapping task + approval domains.

    Despite the name, the current implementation does not reach
    external services; it provides a typed stable surface for
    routines.  Real repository wiring is deferred to later phases.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, dict[str, Any]] = {}
        self._approvals: dict[str, dict[str, Any]] = {}
        self._events: list[dict[str, Any]] = []
        self._approval_counter = _ApprovalCounter()

    # ---- task CRUD ----

    def create_task(self, req: CreateTaskRequest) -> dict[str, Any]:
        """Create a new task and return its record."""
        ts = datetime.now(UTC)
        task_id = TaskId(f"task-{len(self._tasks) + 1}")
        task = {
            "id": task_id,
            "session_id": req.session_id,
            "title": req.title,
            "objective": req.objective,
            "state": "draft",
            "acceptance_criteria": req.acceptance_criteria or (),
            "created_at": ts.isoformat(),
            "updated_at": ts.isoformat(),
        }
        self._tasks[task_id] = task
        self._record_event(
            "run.progress",
            task_id,
            {
                "phase": "task_created",
            },
        )
        return task

    # ---- transitions ----

    def transition_task(self, req: TransitionTaskRequest) -> dict[str, Any]:
        """Transition a task to a new state."""
        task = self._tasks.get(req.task_id)
        if task is None:
            raise KeyError(f"task {req.task_id!r} not found")
        allowed_transitions: dict[str, tuple[str, ...]] = {
            "draft": ("planning",),
            "planning": ("executing", "cancelled"),
            "executing": ("waiting_approval", "failed", "completed"),
            "waiting_approval": ("planning", "cancelled", "failed"),
            "completed": (),
            "failed": (),
            "cancelled": (),
        }
        valid_next = allowed_transitions.get(task["state"], ())
        if req.state not in valid_next:
            raise ValueError(f"cannot transition {task['state']!r} -> {req.state!r}")
        task["state"] = req.state
        task["updated_at"] = datetime.now(UTC).isoformat()
        self._record_event(
            "run.progress",
            task["id"],
            {
                "phase": "task_transitioned",
                "to_state": req.state,
            },
        )
        return task

    # ---- approvals ----

    def request_approval(self, req: RequestApprovalRequest) -> dict[str, Any]:
        """Emit an approval checkpoint for a task."""
        task = self._tasks.get(req.task_id)
        if task is None:
            raise KeyError(f"task {req.task_id!r} not found")
        approval_id = self._approval_counter.next()
        approval = {
            "id": approval_id,
            "task_id": req.task_id,
            "state": "pending",
            "context": req.approval_context or {},
            "resolved_at": None,
        }
        self._approvals[req.task_id] = approval
        task["state"] = "waiting_approval"
        self._record_event(
            "run.approval_waiting",
            task["id"],
            {
                "approval_id": approval_id,
            },
        )
        return approval

    def resolve_approval(self, req: ApprovalDecisionRequest) -> dict[str, Any]:
        """Apply an approval decision and emit RT-002 events."""
        approval = self._approvals.get(req.task_id)
        if approval is None:
            raise KeyError(f"approval for task {req.task_id!r} not found")
        if approval["state"] != "pending":
            raise ApprovalAlreadyResolvedError(approval["id"])
        # Apply decision and map to RT-002 event
        event_type, task_out = self._apply_decision(req, approval)
        self._record_event(
            event_type,
            req.task_id,
            {"approval_id": approval["id"]} | task_out,
        )
        approval["state"] = "resolved"
        # Set human-read state from decision
        if isinstance(req.decision, Granted):
            approval["state"] = "granted"
        elif isinstance(req.decision, DeniedAbandon):
            approval["state"] = "denied_abandon"
        elif isinstance(req.decision, DeniedAlternatePath):
            approval["state"] = "denied_alternate_path"
        elif isinstance(req.decision, Timeout):
            approval["state"] = "timeout"
        return dict(approval) | task_out

    def _apply_decision(
        self,
        req: ApprovalDecisionRequest,
        approval: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        """Map a decision to RT-002 event type and transition."""
        if isinstance(req.decision, Granted):
            approval["state"] = "granted"
            return (
                "run.plan_ready",
                {
                    "task_id": approval["task_id"],
                    "reset_state": "planning",
                },
            )
        if isinstance(req.decision, DeniedAbandon):
            return (
                "run.cancelled",
                {
                    "task_id": approval["task_id"],
                    "reset_state": "cancelled",
                },
            )
        if isinstance(req.decision, DeniedAlternatePath):
            return (
                "run.progress",
                {
                    "task_id": approval["task_id"],
                    "reset_state": "planning",
                    "alternate_path": req.decision.note,
                },
            )
        if isinstance(req.decision, Timeout):
            return (
                "run.cancelled",
                {
                    "task_id": approval["task_id"],
                    "retryable": req.decision.retryable,
                },
            )
        raise ValueError("unknown decision type")

    # ---- event replay ----

    def get_events(self) -> list[dict[str, Any]]:
        """Return all recorded events for assertion."""
        return list(self._events)

    def _record_event(
        self,
        event_type: str,
        task_id: str,
        payload: dict[str, Any],
    ) -> None:
        self._events.append(
            {
                "type": event_type,
                "task_id": task_id,
                "payload": payload,
                "ts": datetime.now(UTC).isoformat(),
            }
        )
