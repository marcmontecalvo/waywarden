"""Async tests for EA scheduler routine.

Uses the async-compatible fake service to prove the scheduler:
- resolves tasks through the EATaskService surface (not direct handler)
- does NOT auto-grant when no explicit decision is given
- handles Granted, DeniedAbandon, DeniedAlternatePath
- handles the no-decision case correctly

Canonical references:
    - P5-FIX-3 #174 (EA routine orchestration wiring)
    - P5-FIX-2 #173 (repository-backed EA task service)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest
from fakes import FakeEATaskService

from waywarden.services.approval_types import (
    DeniedAbandon,
    DeniedAlternatePath,
    Granted,
)
from waywarden.services.orchestration.scheduler import (
    EASchedulerHandler,
    ScheduledTask,
    ScheduleResult,
)

# -----------------------------------------------------------------------
# Schedule with explicit decisions
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_schedule_auto_grant() -> None:
    """With explicit Granted, tasks are approved."""
    tasks = [
        ScheduledTask(title="Task 1", objective="Obj 1"),
        ScheduledTask(title="Task 2", objective="Obj 2"),
    ]
    svc = FakeEATaskService()
    handler = EASchedulerHandler(task_service=svc)
    result = await handler.run(tasks, decisions={"1": Granted()})
    assert result.tasks_processed == 2
    assert result.tasks_approved == 1


@pytest.mark.asyncio
async def test_schedule_respects_response_map() -> None:
    """Explicit deny-abandon should count as denied."""
    tasks = [ScheduledTask(title="my-task", objective="O")]
    svc = FakeEATaskService()
    handler = EASchedulerHandler(task_service=svc)
    decision = await handler.run(
        tasks,
        decisions={"my-task": DeniedAbandon(reason="nope")},
    )
    assert decision.tasks_processed == 1
    assert decision.tasks_approved == 0
    assert decision.tasks_denied == 1


@pytest.mark.asyncio
async def test_schedule_respects_deny_alternate() -> None:
    """Explicit deny-alternate should count as rescheduled."""
    tasks = [ScheduledTask(title="a", objective="O")]
    svc = FakeEATaskService()
    handler = EASchedulerHandler(task_service=svc)
    decision = await handler.run(
        tasks,
        decisions={"a": DeniedAlternatePath(note="alt")},
    )
    assert decision.tasks_rescheduled == 1


@pytest.mark.asyncio
async def test_schedule_empty_list() -> None:
    """Scheduler with no tasks should return zero."""
    svc = FakeEATaskService()
    handler = EASchedulerHandler(task_service=svc)
    result = await handler.run([])
    assert result.tasks_processed == 0
    assert result.tasks_approved == 0


@pytest.mark.asyncio
async def test_schedule_multiple_mixed_outcomes() -> None:
    """Mix of grant, deny-abandon, and deny-alternate."""
    tasks = [
        ScheduledTask(title="grant", objective="O"),
        ScheduledTask(title="deny", objective="O"),
        ScheduledTask(title="resched", objective="O"),
    ]
    svc = FakeEATaskService()
    handler = EASchedulerHandler(task_service=svc)
    result = await handler.run(
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


@pytest.mark.asyncio
async def test_schedule_decisions_recorded() -> None:
    """Every task should have a decision record."""
    svc = FakeEATaskService()
    handler = EASchedulerHandler(task_service=svc)
    result = await handler.run(
        [ScheduledTask(title="x", objective="O")],
        decisions={"1": Granted()},
    )
    assert len(result.decisions) == 1
    assert result.decisions[0]["decision"] == "Granted"
    assert "task_id" in result.decisions[0]


@pytest.mark.asyncio
async def test_schedule_returns_schedule_result_type() -> None:
    """Return value should be a ScheduleResult."""
    svc = FakeEATaskService()
    handler = EASchedulerHandler(task_service=svc)
    result = await handler.run([])
    assert isinstance(result, ScheduleResult)


# -----------------------------------------------------------------------
# No auto-grant guard
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scheduler_no_auto_grant_no_decision() -> None:
    """When no explicit decision is given, the scheduler does NOT grant."""
    tasks = [ScheduledTask(title="must-explicit", objective="O")]
    svc = FakeEATaskService()
    handler = EASchedulerHandler(task_service=svc)
    result = await handler.run(tasks)
    # The default "Accepted" from the old code would count as approved.
    # Now there should be zero approved since no decision was provided.
    assert result.tasks_processed == 1
    assert result.tasks_approved == 0
    # There should be a no-decision milestone record
    assert any(d["decision"] == "none" for d in result.decisions)


@pytest.mark.asyncio
async def test_scheduler_no_decision_with_granted_task() -> None:
    """Mixed: one task with grant, one without."""
    tasks = [
        ScheduledTask(title="granted-task", objective="O"),
        ScheduledTask(title="no-decision", objective="O"),
    ]
    svc = FakeEATaskService()
    handler = EASchedulerHandler(task_service=svc)
    result = await handler.run(
        tasks,
        decisions={"granted-task": Granted()},
    )
    assert result.tasks_processed == 2
    assert result.tasks_approved == 1
    # Second task should NOT be auto-granted
    assert result.tasks_denied == 0
    assert any(d["decision"] == "none" for d in result.decisions)
