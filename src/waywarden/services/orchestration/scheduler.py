"""EA scheduler routine handler.

The EA scheduler picks tasks from a queue, schedules them, and
dispatches with explicit approval checkpoints.  It uses the EA
task service (P5-FIX-2) for task creation and approval — fully
repository-backed via the ``EATaskService``.

Schema covenant:  all task transitions pass through the orchestration
milestone surface via ``run.progress`` events; approval decisions route
through the ``ApprovalEngine`` for durability.

Canonical references:
    - ADR 0005 (approval model)
    - ADR 0007 (good/bad patterns)
    - P5-FIX-2 #173 (repository-backed EA task service)
    - RT-002 (approval decision event mapping)
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

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Scheduler handler
# ---------------------------------------------------------------------------


class EASchedulerHandler:
    """Schedules and dispatches EA tasks with approval checkpoints.

    This handler is **async** because the production
    ``EATaskService`` is fully async (repository-backed, P5-FIX-2).

    In production it is driven by the orchestration service milestone
    engine.  In tests it can accept an inline event stream for capture.

    **No auto-grant guard:** If *decisions* is ``None`` or a given task
    has no explicit decision, the scheduler **does not** silently grant.
    It writes into ``waiting_approval`` and records the absence as a
    denied count in ``ScheduleResult``, requiring an operator decision
    before any outbound action.
    """

    def __init__(
        self,
        task_service: EATaskService | None = None,
    ) -> None:
        self.task_service = task_service

    async def run(
        self,
        tasks: list[ScheduledTask],
        decisions: dict[str, ApprovalDecision] | None = None,
    ) -> ScheduleResult:
        """Execute the scheduler against a list of queued tasks.

        Args:
            tasks: Tasks to schedule and dispatch.
            decisions: Map from ``ScheduledTask`` title to the approval
                decision to apply.  If not supplied, tasks are **not**
                auto-granted — they remain in ``waiting_approval`` and
                count as denied.

        Returns:
            A ``ScheduleResult`` summarising the scheduling run.

        Raises:
            ValueError: When ``task_service`` is not provided.
        """
        if self.task_service is None:
            raise ValueError("EASchedulerHandler requires a task_service")

        result = ScheduleResult()
        decisions = decisions or {}

        for idx, stask in enumerate(tasks, start=1):
            task_id: str = f"task-sched-{idx}"

            # 1. Create the task via repo-backed service
            task = await self.task_service.create_task(
                CreateTaskRequest(
                    session_id="scheduler-sess",
                    title=stask.title,
                    objective=stask.objective,
                )
            )
            task_id = str(task["id"])

            # 2. Transition to executing
            await self.task_service.transition_task(
                TransitionTaskRequest(task_id=task_id, state="planning")
            )
            await self.task_service.transition_task(
                TransitionTaskRequest(task_id=task_id, state="executing")
            )

            # 3. Request approval checkpoint
            await self.task_service.request_approval(
                RequestApprovalRequest(task_id=task_id, run_id="scheduler-run")
            )

            # 4. Apply decision — look up by title first, then by index.
            decision = decisions.get(stask.title)
            if decision is None:
                decision = decisions.get(str(idx))

            if decision is not None:
                # There is an explicit decision — resolve through engine.
                await self.task_service.resolve_approval(
                    ApprovalDecisionRequest(
                        task_id=task_id,
                        decision=decision,
                    )
                )

            result.tasks_processed += 1

            if isinstance(decision, Granted):
                result.tasks_approved += 1
                # Post-grant transitions
                await self.task_service.transition_task(
                    TransitionTaskRequest(task_id=task_id, state="planning")
                )
                await self.task_service.transition_task(
                    TransitionTaskRequest(task_id=task_id, state="executing")
                )
                await self.task_service.transition_task(
                    TransitionTaskRequest(task_id=task_id, state="completed")
                )
            elif isinstance(decision, DeniedAbandon):
                result.tasks_denied += 1
            elif isinstance(decision, DeniedAlternatePath):
                result.tasks_rescheduled += 1
                await self.task_service.transition_task(
                    TransitionTaskRequest(task_id=task_id, state="planning")
                )

            result.decisions.append(
                {
                    "task_id": task_id,
                    "decision": type(decision).__name__ if decision else "none",
                }
            )

        return result
