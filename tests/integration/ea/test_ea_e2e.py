"""Integration test: EA profile end-to-end run (P5-10 #90 → P5-FIX-3 #174).

Exit gate for P5. Drives the full EA profile lifecycle:
briefing → inbox triage → scheduled task with approval checkpoint.

Uses the async-compatible FakeEATaskService to prove the handlers
execute through the EATaskService surface (not direct sync calls).

Asserts:
- Approval engine integration
- Task service lifecycle
- E2E handler composition
"""

import pytest

from tests.unit.fakes import FakeEATaskService
from waywarden.services.approval_types import (
    DeniedAbandon,
    Granted,
)
from waywarden.services.orchestration.briefing import (
    EABriefingHandler,
    InboxEntry,
)
from waywarden.services.orchestration.scheduler import (
    EASchedulerHandler,
    ScheduledTask,
)
from waywarden.services.orchestration.triage import (
    EAIboxTriageHandler,
    InboxItem,
)


@pytest.fixture
def task_service() -> FakeEATaskService:
    return FakeEATaskService()


@pytest.fixture
def briefing_handler() -> EABriefingHandler:
    return EABriefingHandler()


@pytest.fixture
def scheduler_handler(task_service) -> EASchedulerHandler:
    return EASchedulerHandler(task_service=task_service)


@pytest.fixture
def triage_handler(task_service) -> EAIboxTriageHandler:
    return EAIboxTriageHandler(task_service=task_service)


# =======================================================================
# Full EA lifecycle: briefing → triage → scheduling → approval → complete
# =======================================================================


@pytest.mark.asyncio
async def test_ea_e2e_full_lifecycle(
    task_service: FakeEATaskService,
    briefing_handler: EABriefingHandler,
    scheduler_handler: EASchedulerHandler,
    triage_handler: EAIboxTriageHandler,
) -> None:
    """Full EA lifecycle: briefing → inbox triage → scheduling with approval."""
    # 1. Briefing: produces a dated briefing from inbox
    briefing = briefing_handler.run(
        inbox_entries=[
            InboxEntry(
                subject="Meeting rescheduled",
                body="New time: 3pm",
                from_address="boss@example.com",
            ),
        ],
        pending_tasks=0,
    )
    assert briefing.state.inbox_received == 1
    assert briefing.state.inbox_accepted == 1

    # 2. Inbox triage: classify, draft, approve inbox items
    triage = await triage_handler.run(
        items=[
            InboxItem(
                subject="Meeting rescheduled",
                from_address="boss@example.com",
                body="New time: 3pm",
            ),
        ],
        decisions={
            "Meeting rescheduled": Granted(),
        },
    )
    assert triage.items_triaged == 1
    assert triage.items_approved == 1
    assert triage.items[0].approved is True

    # 3. Scheduling: pick up tasks, schedule with approval gate
    scheduler = await scheduler_handler.run(
        tasks=[
            ScheduledTask(
                title="Prepare Q4 budget",
                objective="Gather finance data and draft report",
            ),
        ],
        decisions={
            "Prepare Q4 budget": Granted(),
        },
    )
    assert scheduler.tasks_processed == 1
    assert scheduler.tasks_approved == 1


@pytest.mark.asyncio
async def test_ea_e2e_approval_deny_path(
    task_service: FakeEATaskService,
    scheduler_handler: EASchedulerHandler,
) -> None:
    """EA lifecycle where approval is denied-abandon."""
    # Scheduler with deny-abandon
    result = await scheduler_handler.run(
        tasks=[
            ScheduledTask(
                title="Skip this task",
                objective="Do not do this",
            ),
        ],
        decisions={
            "Skip this task": DeniedAbandon(reason="not needed"),
        },
    )
    assert result.tasks_processed == 1
    assert result.tasks_denied == 1


@pytest.mark.asyncio
async def test_ea_e2e_multi_task_schedule(
    task_service: FakeEATaskService,
) -> None:
    """Multiple tasks go through scheduling pipeline."""
    handler = EASchedulerHandler(task_service=task_service)
    result = await handler.run(
        [
            ScheduledTask(title="Task A", objective="Obj A"),
            ScheduledTask(title="Task B", objective="Obj B"),
            ScheduledTask(title="Task C", objective="Obj C"),
        ],
        decisions={
            "Task A": Granted(),
            "Task B": Granted(),
            "Task C": Granted(),
        },
    )
    assert result.tasks_processed == 3
    assert result.tasks_approved == 3

    # Verify task transitions through events
    events = task_service.get_events()
    transitions = [
        e
        for e in events
        if e["type"] == "run.progress" and e["payload"].get("phase") == "task_transitioned"
    ]
    # Three tasks in the pipeline — at least 3 transitions per task = 9+
    assert len(transitions) >= 9
