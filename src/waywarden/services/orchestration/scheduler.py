"""EA scheduler routine handler.

The EA scheduler picks tasks from a queue, schedules them, and
dispatches with explicit approval checkpoints.  It uses the EA
task service (P5-4) for task creation and approval.

Canonical references:
    - ADR 0005 (approval model)
    - ADR 0007 (good/bad patterns)
    - P5-3 #83 (EA profile)
    - P5-4 #84 (EA task service)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from waywarden.services.approval_types import (
    ApprovalDecision,
    DeniedAbandon,
    DeniedAlternatePath,
    Granted,
)
from waywarden.services.ea_task_service import (
    ApprovalDecisionRequest,
    CreateTaskRequest,
    EATaskService,
    RequestApprovalRequest,
    TransitionTaskRequest,
)


@dataclass(slots=True)
class ScheduledTask:
    """A task in the scheduling queue."""

    title: str
    objective: str
    due_at: str | None = None
    status: str = "queued"


@dataclass(slots=True)
class ScheduleResult:
    """Result of running the scheduler."""

    tasks_processed: int = 0
    tasks_approved: int = 0
    tasks_denied: int = 0
    tasks_rescheduled: int = 0
    decisions: list[dict[str, Any]] = field(default_factory=list)


class EASchedulerHandler:
    """Schedules and dispatches EA tasks with approval checkpoints.

    This handler is synchronous for testability.  In production it
    would be driven by the orchestration service milestone engine.
    """

    def __init__(self, task_service: EATaskService | None = None) -> None:
        self.task_service = task_service or EATaskService()

    def run(
        self,
        tasks: list[ScheduledTask],
        decisions: dict[str, ApprovalDecision] | None = None,
    ) -> ScheduleResult:
        """Execute the scheduler against a list of queued tasks.

        Args:
            tasks: Tasks to schedule and dispatch.
            decisions: Map from ScheduledTask title to the approval
                decision to apply.  If not supplied, all tasks are
                auto-granted.

        Returns:
            A >>ScheduleResult`` summarising the scheduling run.
        """
        result = ScheduleResult()
        decisions = decisions or {}
        for idx, stask in enumerate(tasks, start=1):
            # 1. Create the task
            task = self.task_service.create_task(
                CreateTaskRequest(
                    session_id="scheduler-sess",
                    title=stask.title,
                    objective=stask.objective,
                )
            )
            task_id = task["id"]

            # 2. Transition to executing
            self.task_service.transition_task(
                TransitionTaskRequest(
                    task_id=task_id, state="planning"
                )
            )
            self.task_service.transition_task(
                TransitionTaskRequest(
                    task_id=task_id, state="executing"
                )
            )

            # 3. Request approval checkpoint
            self.task_service.request_approval(
                RequestApprovalRequest(task_id=task_id)
            )

            # 4. Apply decision — look up by title first, then index
            decision = decisions.get(stask.title)
            if decision is None:
                decision = decisions.get(str(idx))
            if decision is None:
                decision = Granted()

            self.task_service.resolve_approval(
                ApprovalDecisionRequest(
                    task_id=task_id,
                    decision=decision,
                )
            )

            result.tasks_processed += 1

            if isinstance(decision, Granted):
                result.tasks_approved += 1
                self.task_service.transition_task(
                    TransitionTaskRequest(
                        task_id=task_id, state="planning"
                    )
                )
                self.task_service.transition_task(
                    TransitionTaskRequest(
                        task_id=task_id, state="executing"
                    )
                )
                self.task_service.transition_task(
                    TransitionTaskRequest(
                        task_id=task_id, state="completed"
                    )
                )
            elif isinstance(decision, DeniedAbandon):
                result.tasks_denied += 1
            elif isinstance(decision, DeniedAlternatePath):
                result.tasks_rescheduled += 1
                self.task_service.transition_task(
                    TransitionTaskRequest(
                        task_id=task_id, state="planning"
                    )
                )
            result.decisions.append({
                "task_id": task_id,
                "decision": type(decision).__name__,
            })

        return result
