"""Tests for EA scheduler routine (P5-6 #86)."""


from waywarden.services.approval_types import (
    DeniedAbandon,
    DeniedAlternatePath,
    Granted,
)
from waywarden.services.ea_task_service import EATaskService
from waywarden.services.orchestration.scheduler import (
    EASchedulerHandler,
    ScheduledTask,
    ScheduleResult,
)

# -----------------------------------------------------------------------
# Schedule with auto-grant
# -----------------------------------------------------------------------


def test_schedule_auto_grant() -> None:
    """With no explicit response, all tasks are granted."""
    tasks = [
        ScheduledTask(title="Task 1", objective="Obj 1"),
        ScheduledTask(title="Task 2", objective="Obj 2"),
    ]
    svc = EATaskService()
    handler = EASchedulerHandler(task_service=svc)
    result = handler.run(tasks)
    assert result.tasks_processed == 2
    assert result.tasks_approved == 2
    assert result.tasks_denied == 0
    assert result.tasks_rescheduled == 0


def test_schedule_respects_response_map() -> None:
    """Explicit deny-abandon should count as denied."""
    tasks = [ScheduledTask(title="my-task", objective="O")]
    svc = EATaskService()
    handler = EASchedulerHandler(task_service=svc)
    decision = handler.run(
        tasks,
        decisions={"my-task": DeniedAbandon(reason="nope")},
    )
    assert decision.tasks_processed == 1
    assert decision.tasks_approved == 0
    assert decision.tasks_denied == 1


def test_schedule_respects_deny_alternate() -> None:
    """Explicit deny-alternate should count as rescheduled."""
    tasks = [ScheduledTask(title="a", objective="O")]
    svc = EATaskService()
    handler = EASchedulerHandler(task_service=svc)
    decision = handler.run(
        tasks,
        decisions={"a": DeniedAlternatePath(note="alt")},
    )
    assert decision.tasks_rescheduled == 1


def test_schedule_empty_list() -> None:
    """Scheduler with no tasks should return zero."""
    handler = EASchedulerHandler()
    result = handler.run([])
    assert result.tasks_processed == 0
    assert result.tasks_approved == 0


def test_schedule_multiple_mixed_outcomes() -> None:
    """Mix of grant, deny-abandon, and deny-alternate."""
    tasks = [
        ScheduledTask(title="grant", objective="O"),
        ScheduledTask(title="deny", objective="O"),
        ScheduledTask(title="resched", objective="O"),
    ]
    svc = EATaskService()
    handler = EASchedulerHandler(task_service=svc)
    result = handler.run(
        tasks,
        decisions={
            "grant": Granted(),
            "deny": DeniedAbandon(reason="no"),
            "resched": DeniedAlternatePath(note="try-alt"),
        },
    )
    assert result.tasks_processed == 3
    assert result.tasks_approved == 1
    assert result.tasks_denied == 1
    assert result.tasks_rescheduled == 1


def test_schedule_decisions_recorded() -> None:
    """Every task should have a decision record."""
    svc = EATaskService()
    handler = EASchedulerHandler(task_service=svc)
    result = handler.run(
        [ScheduledTask(title="x", objective="O")],
    )
    assert len(result.decisions) == 1
    assert result.decisions[0]["decision"] == "Granted"
    assert "task_id" in result.decisions[0]


def test_schedule_returns_schedule_result_type() -> None:
    """Return value should be a ScheduleResult."""
    svc = EATaskService()
    handler = EASchedulerHandler(task_service=svc)
    result = handler.run([])
    assert isinstance(result, ScheduleResult)
