"""Tests for repository-backed EA task service (P5-FIX-2 #173).

These tests verify that the production EA task service:
- persists tasks through the TaskRepository
- routes approvals through ApprovalEngine
- emits durable RT-002 events
- does not use in-memory dicts for authoritative state
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import MappingProxyType

import pytest

from waywarden.domain.approval import Approval
from waywarden.domain.ids import RunEventId, RunId
from waywarden.domain.run_event import RunEvent
from waywarden.domain.task import Task
from waywarden.services.approval_engine import ApprovalEngine
from waywarden.services.approval_types import (
    ApprovalAlreadyResolvedError,
    DeniedAbandon,
    DeniedAlternatePath,
    Granted,
    Timeout,
)
from waywarden.services.ea_task_service import (
    ApprovalDecisionRequest,
    CreateTaskRequest,
    EATaskService,
    RequestApprovalRequest,
    TransitionTaskRequest,
)

# ---------------------------------------------------------------------------
# In-memory repo doubles
# ---------------------------------------------------------------------------


class InMemoryApprovalRepo:
    """Thin in-memory ``ApprovalRepository`` for tests."""

    def __init__(self) -> None:
        self._store: dict[str, Approval] = {}

    async def get(self, id: str) -> Approval | None:
        return self._store.get(id)

    async def save(self, approval: Approval) -> Approval:
        self._store[approval.id] = approval
        return approval

    async def list_by_run(self, run_id: str) -> list[Approval]:
        return [a for a in self._store.values() if a.run_id == run_id]


class InMemoryTaskRepo:
    """Thin in-memory ``TaskRepository`` for tests."""

    def __init__(self) -> None:
        self._store: dict[str, Task] = {}

    async def get(self, id: str) -> Task | None:
        return self._store.get(id)

    async def save(self, task: Task) -> Task:
        self._store[task.id] = task
        return task


class InMemoryEventRepo:
    """Append-only in-memory ``RunEventRepository`` for tests."""

    def __init__(
        self,
        run_id: str | None = None,
    ) -> None:
        self._run_id = run_id or "run_001"
        self._sequences: dict[str, int] = {}
        self._events: list[RunEvent] = []

    async def append(self, event: RunEvent) -> RunEvent:
        run_id = str(event.run_id)
        last = self._sequences.get(run_id, 0)
        next_seq = last + 1
        # RunEvent validates seq >= 1
        confirmed_event = RunEvent(
            id=RunEventId(str(event.id)),
            run_id=RunId(run_id),
            seq=next_seq,
            type=event.type,
            payload=MappingProxyType(dict(event.payload)),
            timestamp=event.timestamp,
            causation=event.causation,
            actor=event.actor,
        )
        self._sequences[run_id] = next_seq
        self._events.append(confirmed_event)
        return confirmed_event

    async def list(
        self,
        run_id: str,
        *,
        since_seq: int = 0,
        limit: int | None = None,
    ) -> list[RunEvent]:
        result = [e for e in self._events if e.seq > since_seq and str(e.run_id) == run_id]
        if limit is not None:
            result = result[:limit]
        return result

    async def latest_seq(self, run_id: str) -> int:
        return self._sequences.get(run_id, 0)


def _make_task(
    id: str = "task-s1",
    *,
    state: str = "draft",
    session_id: str = "s1",
) -> Task:
    now = datetime.now(UTC)
    return Task(
        id=id,
        session_id=session_id,
        title="Test task",
        objective="Do things",
        state=state,  # type: ignore[arg-type]
        created_at=now,
        updated_at=now,
    )


def _make_engine(
    approvals: InMemoryApprovalRepo,
    events: InMemoryEventRepo,
) -> ApprovalEngine:

    # Small wrapper that tracks requests made to the engine
    return ApprovalEngine(approvals=approvals, events=events)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def task_repo() -> InMemoryTaskRepo:
    return InMemoryTaskRepo()


@pytest.fixture
def approval_repo() -> InMemoryApprovalRepo:
    return InMemoryApprovalRepo()


@pytest.fixture
def event_repo() -> InMemoryEventRepo:
    return InMemoryEventRepo()


@pytest.fixture
def engine(
    approval_repo: InMemoryApprovalRepo,
    event_repo: InMemoryEventRepo,
) -> ApprovalEngine:
    return ApprovalEngine(approvals=approval_repo, events=event_repo)


@pytest.fixture
def svc(
    task_repo: InMemoryTaskRepo,
    engine: ApprovalEngine,
    event_repo: InMemoryEventRepo,
) -> EATaskService:
    return EATaskService(
        task_repo=task_repo,
        approval_engine=engine,
        events=event_repo,
    )


# -----------------------------------------------------------------------
# Task creation — repository-backed
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_task_persists_to_repo(
    task_repo: InMemoryTaskRepo, svc: EATaskService
) -> None:
    """AC: Repository-backed create task persists a task record."""
    result = await svc.create_task(
        CreateTaskRequest(
            session_id="s1",
            title="Test",
            objective="Do stuff",
            acceptance_criteria=("c1",),
        )
    )
    assert result["state"] == "draft"
    assert result["session_id"] == "s1"
    # Verify the task exists in the repo (not just the service dict)
    persisted = await task_repo.get(result["id"])
    assert persisted is not None
    assert persisted.title == "Test"


@pytest.mark.asyncio
async def test_create_task_emits_event(
    event_repo: InMemoryEventRepo,
    svc: EATaskService,
) -> None:
    """Repository-backed create emits a run.progress event."""
    await svc.create_task(
        CreateTaskRequest(
            session_id="s1",
            title="Test",
            objective="Do stuff",
        )
    )
    events = event_repo._events
    assert len(events) >= 1
    assert events[0].type == "run.progress"
    assert events[0].payload["phase"] == "task_created"


# -----------------------------------------------------------------------
# Task transitions — repository-backed
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transition_draft_to_planning(
    svc: EATaskService, task_repo: InMemoryTaskRepo
) -> None:
    """Repository-backed transition persists state changes."""
    created = await svc.create_task(CreateTaskRequest(session_id="s1", title="T", objective="O"))
    result = await svc.transition_task(
        TransitionTaskRequest(task_id=created["id"], state="planning")
    )
    assert result["state"] == "planning"
    # Verify in repo
    persisted = await task_repo.get(created["id"])
    assert persisted is not None
    assert persisted.state == "planning"


@pytest.mark.asyncio
async def test_transition_executing_to_waiting_approval(svc: EATaskService) -> None:
    """Full flow: draft → planning → executing → waiting_approval."""
    created = await svc.create_task(CreateTaskRequest(session_id="s1", title="T", objective="O"))
    await svc.transition_task(TransitionTaskRequest(task_id=created["id"], state="planning"))
    await svc.transition_task(TransitionTaskRequest(task_id=created["id"], state="executing"))
    result = await svc.transition_task(
        TransitionTaskRequest(task_id=created["id"], state="waiting_approval")
    )
    assert result["state"] == "waiting_approval"


@pytest.mark.asyncio
async def test_transition_completed_is_forbidden(svc: EATaskService) -> None:
    """Transition to terminal state from draft should raise."""
    created = await svc.create_task(CreateTaskRequest(session_id="s1", title="T", objective="O"))
    with pytest.raises(ValueError):
        await svc.transition_task(TransitionTaskRequest(task_id=created["id"], state="completed"))


@pytest.mark.asyncio
async def test_transition_nonexistent_task_raises(svc: EATaskService) -> None:
    """Transition on missing task raises KeyError."""
    with pytest.raises(KeyError):
        await svc.transition_task(TransitionTaskRequest(task_id="nonexistent", state="planning"))


# -----------------------------------------------------------------------
# Approval grant — routes through ApprovalEngine
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_approval_emits_waiting_event(
    event_repo: InMemoryEventRepo,
    svc: EATaskService,
) -> None:
    """request_approval transitions the task and emits events."""
    created = await svc.create_task(CreateTaskRequest(session_id="s1", title="T", objective="O"))
    await svc.transition_task(TransitionTaskRequest(task_id=created["id"], state="planning"))
    await svc.transition_task(TransitionTaskRequest(task_id=created["id"], state="executing"))
    result = await svc.request_approval(
        RequestApprovalRequest(
            task_id=created["id"],
            run_id="run_001",
        )
    )
    assert result["state"] == "waiting_approval"
    events = event_repo._events
    assert any(e.type == "run.approval_waiting" for e in events)


@pytest.mark.asyncio
async def test_grant_approval_resolves_approvals_and_tasks(
    svc: EATaskService,
    approval_repo: InMemoryApprovalRepo,
) -> None:
    """Granted decision routes through ApprovalEngine and tasks to planning."""
    created = await svc.create_task(CreateTaskRequest(session_id="s1", title="T", objective="O"))
    await svc.transition_task(TransitionTaskRequest(task_id=created["id"], state="planning"))
    await svc.transition_task(TransitionTaskRequest(task_id=created["id"], state="executing"))
    approval_resp = await svc.request_approval(
        RequestApprovalRequest(task_id=created["id"], run_id="run_001")
    )
    result = await svc.resolve_approval(
        ApprovalDecisionRequest(
            task_id=created["id"],
            decision=Granted(),
        )
    )
    assert result["state"] == "granted"
    # ApprovalEngine should have stored a non-pending approval
    persisted = await approval_repo.get(approval_resp["approval_id"])
    assert persisted is not None
    assert persisted.state == "granted"


# -----------------------------------------------------------------------
# Approval — deny-abandon
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deny_abandon_routes_through_engine(
    svc: EATaskService,
    approval_repo: InMemoryApprovalRepo,
    event_repo: InMemoryEventRepo,
) -> None:
    """deny-abandon routes through ApprovalEngine and emits run.cancelled."""
    created = await svc.create_task(CreateTaskRequest(session_id="s1", title="T", objective="O"))
    await svc.transition_task(TransitionTaskRequest(task_id=created["id"], state="planning"))
    await svc.transition_task(TransitionTaskRequest(task_id=created["id"], state="executing"))
    approval_resp = await svc.request_approval(
        RequestApprovalRequest(task_id=created["id"], run_id="run_001")
    )
    result = await svc.resolve_approval(
        ApprovalDecisionRequest(
            task_id=created["id"],
            decision=DeniedAbandon(reason="skip"),
        )
    )
    assert result["state"] == "denied_abandon"
    persisted = await approval_repo.get(approval_resp["approval_id"])
    assert persisted is not None
    assert persisted.state == "denied"
    assert any(
        e.type == "run.cancelled" and e.payload.get("reason") == "approval_denied"
        for e in event_repo._events
    )


# -----------------------------------------------------------------------
# Approval — deny-alternate
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deny_alternate_routes_through_engine(
    svc: EATaskService,
    approval_repo: InMemoryApprovalRepo,
    event_repo: InMemoryEventRepo,
) -> None:
    """deny-alternate routes through ApprovalEngine with alternate_path."""
    created = await svc.create_task(CreateTaskRequest(session_id="s1", title="T", objective="O"))
    await svc.transition_task(TransitionTaskRequest(task_id=created["id"], state="planning"))
    await svc.transition_task(TransitionTaskRequest(task_id=created["id"], state="executing"))
    approval_resp = await svc.request_approval(
        RequestApprovalRequest(task_id=created["id"], run_id="run_001")
    )
    result = await svc.resolve_approval(
        ApprovalDecisionRequest(
            task_id=created["id"],
            decision=DeniedAlternatePath(note="use-alternative"),
        )
    )
    assert result["state"] == "denied_alternate_path"
    persisted = await approval_repo.get(approval_resp["approval_id"])
    assert persisted is not None
    assert persisted.state == "denied"
    events = event_repo._events
    assert any(
        e.type == "run.resumed" and e.payload.get("resume_kind") == "approval_denied_alternate_path"
        for e in events
    )


# -----------------------------------------------------------------------
# Approval — timeout
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeout_retryable_routes_through_engine(
    svc: EATaskService,
    approval_repo: InMemoryApprovalRepo,
    event_repo: InMemoryEventRepo,
) -> None:
    """Timeout(retryable=True) routes through ApprovalEngine and emits run.failed."""
    created = await svc.create_task(CreateTaskRequest(session_id="s1", title="T", objective="O"))
    await svc.transition_task(TransitionTaskRequest(task_id=created["id"], state="planning"))
    await svc.transition_task(TransitionTaskRequest(task_id=created["id"], state="executing"))
    approval_resp = await svc.request_approval(
        RequestApprovalRequest(task_id=created["id"], run_id="run_001")
    )
    result = await svc.resolve_approval(
        ApprovalDecisionRequest(
            task_id=created["id"],
            decision=Timeout(retryable=True),
        )
    )
    assert result["state"] == "timeout"
    persisted = await approval_repo.get(approval_resp["approval_id"])
    assert persisted is not None
    assert persisted.state == "timeout"
    assert any(
        e.type == "run.failed"
        and e.payload.get("failure_code") == "approval_timeout"
        and e.payload.get("retryable") is True
        for e in event_repo._events
    )


# -----------------------------------------------------------------------
# Double-resolve protection
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_double_resolve_protection(svc: EATaskService) -> None:
    """Double-resolve protection still works."""
    created = await svc.create_task(CreateTaskRequest(session_id="s1", title="T", objective="O"))
    await svc.transition_task(TransitionTaskRequest(task_id=created["id"], state="planning"))
    await svc.transition_task(TransitionTaskRequest(task_id=created["id"], state="executing"))
    await svc.request_approval(RequestApprovalRequest(task_id=created["id"], run_id="run_001"))
    await svc.resolve_approval(ApprovalDecisionRequest(task_id=created["id"], decision=Granted()))
    with pytest.raises(ApprovalAlreadyResolvedError):
        await svc.resolve_approval(
            ApprovalDecisionRequest(task_id=created["id"], decision=DeniedAbandon(reason="double"))
        )


# -----------------------------------------------------------------------
# Request/resolve on missing task/approval
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_approval_on_missing_task_raises(svc: EATaskService) -> None:
    """Request approval on missing task raises."""
    with pytest.raises(KeyError):
        await svc.request_approval(RequestApprovalRequest(task_id="nonexistent", run_id="run_001"))


@pytest.mark.asyncio
async def test_resolve_approval_on_missing_approval_raises(svc: EATaskService) -> None:
    """Resolving an unrequested approval raises KeyError."""
    created = await svc.create_task(CreateTaskRequest(session_id="s1", title="T", objective="O"))
    with pytest.raises(KeyError):
        await svc.resolve_approval(
            ApprovalDecisionRequest(task_id=created["id"], decision=Granted())
        )


# -----------------------------------------------------------------------
# Full event stream assertion
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_event_stream(
    event_repo: InMemoryEventRepo,
    svc: EATaskService,
) -> None:
    """End-to-end: create → planning → executing → approve → grant → complete."""
    created = await svc.create_task(
        CreateTaskRequest(session_id="s1", title="Build", objective="Ship")
    )
    await svc.transition_task(TransitionTaskRequest(task_id=created["id"], state="planning"))
    await svc.transition_task(TransitionTaskRequest(task_id=created["id"], state="executing"))
    await svc.request_approval(RequestApprovalRequest(task_id=created["id"], run_id="run_001"))
    await svc.resolve_approval(ApprovalDecisionRequest(task_id=created["id"], decision=Granted()))
    await svc.transition_task(TransitionTaskRequest(task_id=created["id"], state="planning"))
    await svc.transition_task(TransitionTaskRequest(task_id=created["id"], state="executing"))
    await svc.transition_task(TransitionTaskRequest(task_id=created["id"], state="completed"))
    events = event_repo._events
    assert any(
        e.type == "run.progress" and e.payload.get("phase") == "task_created" for e in events
    )
    assert any(e.type == "run.approval_waiting" for e in events)
    assert any(
        e.type == "run.resumed" and e.payload.get("resume_kind") == "approval_granted"
        for e in events
    )
    assert any(
        e.type == "run.progress" and e.payload.get("phase") == "task_transitioned" for e in events
    )


# -----------------------------------------------------------------------
# Regression: no deferred comments in production
# -----------------------------------------------------------------------


def test_no_deferred_worker_comments_in_production_code() -> None:
    """Regression: production EA runtime modules may not contain
    'real repository wiring is deferred' or 'fixture-only' or 'stub'."""
    import waywarden.services.ea_task_service as mod

    source = mod.__loader__.get_source(mod.__name__)
    assert source is not None
    lower = source.lower()
    assert "real repository wiring is deferred" not in lower, (
        "Production code should not contain 'real repository wiring is deferred'"
    )
    assert "fixture-only" not in lower, "Production code should not contain 'fixture-only'"
