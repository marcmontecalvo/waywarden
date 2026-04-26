"""Synchronous fake implementations for the EA task service.

These mocks satisfy the synchronous interfaces used by the
orchestration handler tests (triage, scheduler) while the
real EATaskService is fully async.

Do not use these in production code; they exist only to keep
existing handler tests green while the new repository-backed
service is wired in behind the real interfaces.

This file lives in tests/ and is not part of the production
runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from waywarden.domain.ids import TaskId
from waywarden.services.approval_types import Granted
from waywarden.services.ea_task_service import (
    ApprovalDecisionRequest,
    CreateTaskRequest,
    RequestApprovalRequest,
    TransitionTaskRequest,
)


@dataclass(slots=True)
class FakeEATaskService:
    """Synchronous in-memory fake for synchronous handler tests."""

    _tasks: dict[str, dict[str, Any]] = field(default_factory=dict)
    _approvals: dict[str, dict[str, Any]] = field(default_factory=dict)
    _events: list[dict[str, Any]] = field(default_factory=list)
    _counter: int = 0

    def create_task(self, req: CreateTaskRequest) -> dict[str, Any]:
        self._counter += 1
        task_id = str(TaskId(f"fake-task-{self._counter}"))
        task = {
            "id": task_id,
            "session_id": req.session_id,
            "title": req.title,
            "objective": req.objective,
            "state": "draft",
            "accepted": req.acceptance_criteria or (),
        }
        self._tasks[task_id] = task
        self._events.append(
            {
                "type": "run.progress",
                "payload": {"phase": "task_created"},
                "ts": datetime.now(UTC).isoformat(),
            }
        )
        return task

    def transition_task(self, req: TransitionTaskRequest) -> dict[str, Any]:
        task = self._tasks.get(req.task_id)
        if task is None:
            raise KeyError(f"task {req.task_id!r} not found")
        allowed: dict[str, tuple[str, ...]] = {
            "draft": ("planning",),
            "planning": ("executing", "cancelled"),
            "executing": ("waiting_approval", "failed", "completed"),
            "waiting_approval": ("planning", "cancelled", "failed"),
            "completed": (),
            "failed": (),
            "cancelled": (),
        }
        if req.state not in allowed.get(task["state"], ()):
            raise ValueError(f"cannot transition {task['state']!r} -> {req.state!r}")
        task["state"] = req.state
        self._events.append(
            {
                "type": "run.progress",
                "payload": {"phase": "task_transitioned", "to_state": req.state},
                "ts": datetime.now(UTC).isoformat(),
            }
        )
        return task

    def request_approval(self, req: RequestApprovalRequest) -> dict[str, Any]:
        task = self._tasks.get(req.task_id)
        if task is None:
            raise KeyError(f"task {req.task_id!r} not found")
        approval_id = f"approval-{len(self._approvals)}"
        self._approvals[req.task_id] = dict(id=approval_id, task_id=req.task_id, state="pending")
        task["state"] = "waiting_approval"
        self._events.append(
            {
                "type": "run.approval_waiting",
                "payload": {},
                "ts": datetime.now(UTC).isoformat(),
            }
        )
        return {"task_id": req.task_id, "approval_id": approval_id}

    def resolve_approval(self, req: ApprovalDecisionRequest) -> dict[str, Any]:
        approval = self._approvals.get(req.task_id)
        if approval is None:
            raise KeyError(f"approval for task {req.task_id!r} not found")
        if approval["state"] == "resolved":
            from waywarden.services.approval_types import ApprovalAlreadyResolvedError

            raise ApprovalAlreadyResolvedError(approval_id=approval["id"])
        approval["state"] = "resolved"
        decision = req.decision
        if isinstance(decision, Granted):
            return {"task_id": req.task_id, "state": "granted"}
        return {"task_id": req.task_id, "state": str(type(decision).__name__)}

    def get_events(self) -> list[dict[str, Any]]:
        return list(self._events)
