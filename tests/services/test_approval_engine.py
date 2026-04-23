"""Tests for ApprovalEngine — RT-002 approval decision event mapping.

All tests are @pytest.mark.integration because they must exercise
the full approval → event emission path.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from waywarden.domain.approval import Approval
from waywarden.domain.ids import ApprovalId
from waywarden.domain.run_event import RunEvent
from waywarden.services.approval_engine import ApprovalEngine
from waywarden.services.approval_types import (
    ApprovalAlreadyResolvedError,
    DeniedAbandon,
    DeniedAlternatePath,
    Granted,
    Timeout,
)

# ---------------------------------------------------------------------------
# In-memory repo doubles for testing
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


class InMemoryEventRepo:
    """Append-only in-memory ``RunEventRepository`` for tests."""

    def __init__(self, run_id: str) -> None:
        self._run_id = run_id
        self._events: list[RunEvent] = []

    async def append(self, event: RunEvent) -> RunEvent:
        # Simulate seq assignment
        next_seq = len(self._events) + 1
        event_with_seq = RunEvent(
            id=event.id,
            run_id=event.run_id,
            seq=next_seq,
            type=event.type,
            payload=dict(event.payload),
            timestamp=event.timestamp,
            causation=event.causation,
            actor=event.actor,
        )
        self._events.append(event_with_seq)
        return event_with_seq

    async def list(
        self,
        run_id: str,
        *,
        since_seq: int = 0,
        limit: int | None = None,
    ) -> list[RunEvent]:
        result = [e for e in self._events if e.seq > since_seq]
        if limit is not None:
            result = result[:limit]
        return result

    async def latest_seq(self, run_id: str) -> int:
        return len(self._events)


def _make_approval(
    run_id: str = "run_001",
    approval_id: str = "approval-run_001-test",
    state: str = "pending",
) -> Approval:
    now = datetime.now(UTC)
    return Approval(
        id=ApprovalId(approval_id),
        run_id=run_id,
        approval_kind="test",
        requested_capability="exec_script",
        summary="Run deployment script",
        state=state,
        requested_at=now,
        decided_at=now if state != "pending" else None,
        decided_by=None if state == "pending" else "operator-1",
        expires_at=None,
    )


@pytest.fixture
def approvals() -> InMemoryApprovalRepo:
    return InMemoryApprovalRepo()


@pytest.fixture
def events() -> InMemoryEventRepo:
    return InMemoryEventRepo("run_001")


@pytest.fixture
def engine(approvals: InMemoryApprovalRepo, events: InMemoryEventRepo) -> ApprovalEngine:
    return ApprovalEngine(approvals=approvals, events=events)


class TestRequestEmitsWaitingEvent:
    """P3-7 AC1: request(...) emits run.approval_waiting event."""

    @pytest.mark.integration
    async def test_request_emits_waiting_event(
        self,
        engine: ApprovalEngine,
        events: InMemoryEventRepo,
    ) -> None:
        approval = await engine.request(
            run_id="run_001",
            approval_kind="deploy",
            summary="Deploy to production",
            requested_capability="exec_script",
        )

        assert approval.state == "pending"
        assert len(events._events) == 1

        event = events._events[0]
        assert event.type == "run.approval_waiting"
        assert event.payload["approval_id"] == approval.id
        assert event.payload["approval_kind"] == "deploy"
        assert event.payload["summary"] == "Deploy to production"


class TestGrantedResolvesToResumed:
    """P3-7 AC2: resolve(Granted) emits run.resumed(resume_kind=approval_granted)."""

    @pytest.mark.integration
    async def test_granted_resolves_to_resumed(
        self,
        engine: ApprovalEngine,
        approvals: InMemoryApprovalRepo,
        events: InMemoryEventRepo,
    ) -> None:
        await engine.request(
            run_id="run_001",
            approval_kind="deploy",
            summary="Deploy to production",
        )

        approval = await approvals.get("approval-run_001-deploy")
        assert approval is not None

        result_event = await engine.resolve(approval.id, Granted())

        # Approval state should be granted
        persisted = await approvals.get(approval.id)
        assert persisted.state == "granted"

        # Should be a resumed event with correct resume_kind
        assert result_event.type == "run.resumed"
        assert result_event.payload["resume_kind"] == "approval_granted"
        assert "approval_id" in result_event.payload


class TestDeniedAbandonResolvesToCancelled:
    """P3-7 AC3: resolve(DeniedAbandon) emits run.cancelled(reason=approval_denied)."""

    @pytest.mark.integration
    async def test_denied_abandon_resolves_to_cancelled(
        self,
        engine: ApprovalEngine,
        approvals: InMemoryApprovalRepo,
        events: InMemoryEventRepo,
    ) -> None:
        await engine.request(
            run_id="run_001",
            approval_kind="deploy",
            summary="Deploy to production",
        )

        approval = await approvals.get("approval-run_001-deploy")
        assert approval is not None

        result_event = await engine.resolve(approval.id, DeniedAbandon(reason="not ready"))

        persisted = await approvals.get(approval.id)
        assert persisted.state == "denied"

        assert result_event.type == "run.cancelled"
        assert result_event.payload["reason"] == "approval_denied"


class TestDeniedAlternateResolvesToResumedAlternate:
    """P3-7 AC4: resolve(DeniedAlternatePath) emits
    run.resumed(resume_kind=approval_denied_alternate_path)."""

    @pytest.mark.integration
    async def test_denied_alternate_resolves_to_resumed_alternate(
        self,
        engine: ApprovalEngine,
        approvals: InMemoryApprovalRepo,
        events: InMemoryEventRepo,
    ) -> None:
        await engine.request(
            run_id="run_001",
            approval_kind="deploy",
            summary="Deploy to production",
        )

        approval = await approvals.get("approval-run_001-deploy")
        assert approval is not None

        result_event = await engine.resolve(
            approval.id,
            DeniedAlternatePath(note="use staging instead"),
        )

        persisted = await approvals.get(approval.id)
        assert persisted.state == "denied"

        assert result_event.type == "run.resumed"
        assert result_event.payload["resume_kind"] == "approval_denied_alternate_path"
        assert "approval_id" in result_event.payload


class TestTimeoutRetryableMapsToFailed:
    """P3-7 AC5: resolve(Timeout(retryable=True)) emits run.failed."""

    @pytest.mark.integration
    async def test_timeout_retryable_maps_to_failed(
        self,
        engine: ApprovalEngine,
        approvals: InMemoryApprovalRepo,
        events: InMemoryEventRepo,
    ) -> None:
        await engine.request(
            run_id="run_001",
            approval_kind="deploy",
            summary="Deploy to production",
        )

        approval = await approvals.get("approval-run_001-deploy")
        assert approval is not None

        result_event = await engine.resolve(approval.id, Timeout(retryable=True))

        persisted = await approvals.get(approval.id)
        assert persisted.state == "timeout"

        assert result_event.type == "run.failed"
        assert result_event.payload["failure_code"] == "approval_timeout"
        assert result_event.payload["retryable"] is True


class TestTimeoutNonRetryableMapsToCancelled:
    """P3-7 AC6: resolve(Timeout(retryable=False)) emits run.cancelled."""

    @pytest.mark.integration
    async def test_timeout_non_retryable_maps_to_cancelled(
        self,
        engine: ApprovalEngine,
        approvals: InMemoryApprovalRepo,
        events: InMemoryEventRepo,
    ) -> None:
        await engine.request(
            run_id="run_001",
            approval_kind="deploy",
            summary="Deploy to production",
        )

        approval = await approvals.get("approval-run_001-deploy")
        assert approval is not None

        result_event = await engine.resolve(approval.id, Timeout(retryable=False))

        persisted = await approvals.get(approval.id)
        assert persisted.state == "timeout"

        assert result_event.type == "run.cancelled"
        assert result_event.payload["reason"] == "approval_timeout"


class TestDoubleResolveRejected:
    """P3-7 AC7: Second resolve on the same approval raises ApprovalAlreadyResolvedError."""

    @pytest.mark.integration
    async def test_double_resolve_rejected(
        self,
        engine: ApprovalEngine,
        approvals: InMemoryApprovalRepo,
    ) -> None:
        await engine.request(
            run_id="run_001",
            approval_kind="deploy",
            summary="Deploy to production",
        )

        approval = await approvals.get("approval-run_001-deploy")
        assert approval is not None

        # First resolve succeeds
        await engine.resolve(approval.id, Granted())

        # Second resolve must fail
        with pytest.raises(ApprovalAlreadyResolvedError) as exc_info:
            await engine.resolve(approval.id, DeniedAbandon(reason="too late"))

        assert exc_info.value.approval_id == approval.id
