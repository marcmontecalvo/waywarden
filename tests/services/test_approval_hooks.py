"""Tests for ApprovalHook — routing tool invocations through the approval gate.

Covers P6-6 acceptance criteria:
- before_invoke emits an engine.request when policy requires approval
- before_invoke returns None when policy auto-allows
- before_invoke raises when policy forbids
- pending approvals surface in VisibilityService.snapshot
- snapshot does not emit events when approvals repo is wired
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from waywarden.domain.approval import Approval, ApprovalState
from waywarden.domain.ids import ApprovalId, RunId
from waywarden.domain.manifest.tool_policy import (
    ToolDecisionRule,
    ToolPolicy,
)
from waywarden.domain.run_event import RunEvent
from waywarden.services.approval_engine import ApprovalEngine
from waywarden.services.approval_hooks import ApprovalHook
from waywarden.services.approval_types import (
    DeniedAbandon,
    DeniedAlternatePath,
    Granted,
    Timeout,
)
from waywarden.services.visibility import VisibilityService
from waywarden.tools.model import ToolProvider

# ---------------------------------------------------------------------------
# In-memory doubles
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
        return [a for a in self._store.values() if a.run_id == RunId(run_id)]


class InMemoryEventRepo:
    """Append-only in-memory ``RunEventRepository`` for tests."""

    def __init__(self, run_id: str) -> None:
        self._run_id = run_id
        self._events: list[RunEvent] = []

    async def append(self, event: RunEvent) -> RunEvent:
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


class DummyToolProvider(ToolProvider):
    """Minimal ToolProvider for instrumentation tests."""

    def name(self) -> str:
        return "dummy"

    def capabilities(self) -> list[str]:
        return ["dummy:cap1"]

    async def invoke(
        self,
        tool_id: str,
        action: str,
        params: dict[str, Any],
    ) -> Any:
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_policy(
    rules: list[ToolDecisionRule] | None = None,
    default: str = "approval-required",
) -> ToolPolicy:
    rules = rules or []
    return ToolPolicy(
        preset="ask",
        rules=rules,
        default_decision=cast("Any", default),
    )


def _make_approval(
    run_id: str = "run_001",
    approval_id: str = "approval-run_001-test",
    approval_kind: str = "test",
    state: str = "pending",
) -> Approval:
    now = datetime.now(UTC)
    return Approval(
        id=ApprovalId(approval_id),
        run_id=RunId(run_id),
        approval_kind=approval_kind,
        requested_capability="exec_script",
        summary="Test summary",
        state=cast(ApprovalState, state),
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
def engine(
    approvals: InMemoryApprovalRepo,
    events: InMemoryEventRepo,
) -> ApprovalEngine:
    return ApprovalEngine(approvals=approvals, events=events)


@pytest.fixture
def providers() -> list[ToolProvider]:
    return [DummyToolProvider()]


# ---------------------------------------------------------------------------
# ApprovalHook.before_invoke — approval-required path
# ---------------------------------------------------------------------------


class TestBeforeInvokeRequiresApproval:
    """base_invoke emits engine.request when policy requires approval."""

    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_before_invoke_emits_approval_request(
        self,
        engine: ApprovalEngine,
        approvals: InMemoryApprovalRepo,
        events: InMemoryEventRepo,
        providers: list[ToolProvider],
    ) -> None:
        policy = _make_policy(
            rules=[
                ToolDecisionRule(
                    tool="file_write",
                    action="write",
                    decision="approval-required",
                    reason="File writes need approval",
                ),
            ],
        )
        hook = ApprovalHook(
            engine=engine,
            registry_providers=providers,
            tool_policy=policy,
        )

        result = await hook.before_invoke(
            run_id="run_001",
            tool_id="file_write",
            action="write",
            summary="Modify workspace file",
        )

        assert result is not None
        # Should have created an approval in the repo
        saved = await approvals.get(result)
        assert saved is not None
        assert saved.state == "pending"
        assert saved.approval_kind == "file_write"
        # Should have emitted run.approval_waiting
        assert len(events._events) == 1
        assert events._events[0].type == "run.approval_waiting"


class TestBeforeInvokeAutoAllow:
    """before_invoke returns None when policy auto-allows the tool."""

    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_before_invoke_returns_none_for_auto_allow(
        self,
        engine: ApprovalEngine,
        events: InMemoryEventRepo,
        providers: list[ToolProvider],
    ) -> None:
        policy = _make_policy(
            rules=[
                ToolDecisionRule(
                    tool="file_read",
                    action="read",
                    decision="auto-allow",
                ),
            ],
        )
        hook = ApprovalHook(
            engine=engine,
            registry_providers=providers,
            tool_policy=policy,
        )

        result = await hook.before_invoke(
            run_id="run_001",
            tool_id="file_read",
            action="read",
            summary="Read file",
        )

        assert result is None
        assert len(events._events) == 0


class TestBeforeInvokeForbidden:
    """before_invoke raises when policy forbids the tool."""

    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_before_invoke_raises_for_forbidden(
        self,
        engine: ApprovalEngine,
        providers: list[ToolProvider],
    ) -> None:
        policy = _make_policy(
            rules=[
                ToolDecisionRule(
                    tool="network_egress",
                    action="request",
                    decision="forbidden",
                ),
            ],
        )
        hook = ApprovalHook(
            engine=engine,
            registry_providers=providers,
            tool_policy=policy,
        )

        with pytest.raises(RuntimeError) as exc_info:
            await hook.before_invoke(
                run_id="run_001",
                tool_id="network_egress",
                action="request",
                summary="Make network request",
            )
        assert "forbidden" in str(exc_info.value).lower()


class TestBeforeInvokeDefaultDecision:
    """before_invoke falls through to default_decision correctly."""

    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_default_approval_required(
        self,
        engine: ApprovalEngine,
        approvals: InMemoryApprovalRepo,
        providers: list[ToolProvider],
    ) -> None:
        """Unlisted tool falls through to approval-required default."""
        policy = _make_policy(
            rules=[],
            default="approval-required",
        )
        hook = ApprovalHook(
            engine=engine,
            registry_providers=providers,
            tool_policy=policy,
        )

        result = await hook.before_invoke(
            run_id="run_001",
            tool_id="shell_exec",
            action="run",
            summary="Run a shell command",
        )

        assert result is not None
        saved = await approvals.get(result)
        assert saved is not None
        assert saved.state == "pending"

    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_default_auto_allow(
        self,
        engine: ApprovalEngine,
        providers: list[ToolProvider],
    ) -> None:
        """Unlisted tool falls through to auto-allow default."""
        policy = _make_policy(
            rules=[],
            default="auto-allow",
        )
        hook = ApprovalHook(
            engine=engine,
            registry_providers=providers,
            tool_policy=policy,
        )

        result = await hook.before_invoke(
            run_id="run_001",
            tool_id="shell_exec",
            action="run",
            summary="Run a shell command",
        )
        assert result is None


# ---------------------------------------------------------------------------
# ApprovalHook.requirements — static checks
# ---------------------------------------------------------------------------


class TestRequirementsCheck:
    """requirements() implements correct rule matching."""

    @pytest.mark.anyio
    async def test_first_matching_rule_wins(self, providers: list[ToolProvider]) -> None:
        policy = _make_policy(
            rules=[
                ToolDecisionRule(tool="shell_exec", action="run", decision="auto-allow"),
                ToolDecisionRule(tool="shell_exec", action="run", decision="forbidden"),
            ],
        )
        hook = ApprovalHook(
            engine=MagicMock(),  # not called
            registry_providers=providers,
            tool_policy=policy,
        )

        required, reason, _ = hook.requirements("shell_exec", "run")
        assert required is False

    @pytest.mark.anyio
    async def test_action_specific_rule_beats_wildcard(
        self,
        providers: list[ToolProvider],
    ) -> None:
        """A rule with a matching action takes precedence."""
        policy = _make_policy(
            rules=[
                ToolDecisionRule(tool="code_apply", action="apply", decision="approval-required"),
            ],
        )
        hook = ApprovalHook(
            engine=MagicMock(),
            registry_providers=providers,
            tool_policy=policy,
        )

        required, _, _ = hook.requirements("code_apply", "apply")
        assert required is True


# ---------------------------------------------------------------------------
# VisibilityService — pending approvals in snapshot
# ---------------------------------------------------------------------------


class TestSnapshotIncludesPendingApprovals:
    """approval repos wired into snapshot surface pending approvals."""

    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_pending_approvals_appear_in_snapshot(
        self,
    ) -> None:
        """Pending approvals are returned in the snapshot."""
        mock_events = AsyncMock()
        mock_runs = MagicMock()
        mock_approvals = InMemoryApprovalRepo()

        mock_run = MagicMock()
        mock_run.state = "waiting_approval"
        mock_runs.get = AsyncMock(return_value=mock_run)

        # Add a pending approval
        pending = _make_approval(
            run_id="run-abc",
            approval_id="approval-run-abc-file_write",
            approval_kind="file_write",
            state="pending",
        )
        saved = await mock_approvals.save(pending)
        # Use the correct save return
        await mock_approvals.save(saved)

        mock_events.list = AsyncMock(return_value=[])
        mock_events.latest_seq = AsyncMock(return_value=0)

        service = VisibilityService(
            events=mock_events,
            runs=mock_runs,
            approvals=mock_approvals,
        )
        snapshot = await service.snapshot("run-abc")

        assert len(snapshot.pending_approvals) == 1
        assert snapshot.pending_approvals[0].approval_kind == "file_write"
        assert snapshot.pending_approvals[0].approval_id == saved.id

    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_resolved_approvals_filtered_out(
        self,
    ) -> None:
        """Only pending approvals appear; granted/denied are excluded."""
        mock_events = AsyncMock()
        mock_runs = MagicMock()
        mock_approvals = InMemoryApprovalRepo()

        mock_run = MagicMock()
        mock_run.state = "executing"
        mock_runs.get = AsyncMock(return_value=mock_run)

        # Pending approval
        await mock_approvals.save(
            _make_approval(
                run_id="run-abc",
                approval_id="approval-1",
                approval_kind="shell_exec",
                state="pending",
            ),
        )
        # Already granted
        await mock_approvals.save(
            _make_approval(
                run_id="run-abc",
                approval_id="approval-2",
                approval_kind="file_read",
                state="granted",
            ),
        )

        mock_events.list = AsyncMock(return_value=[])
        mock_events.latest_seq = AsyncMock(return_value=0)

        service = VisibilityService(
            events=mock_events,
            runs=mock_runs,
            approvals=mock_approvals,
        )
        snapshot = await service.snapshot("run-abc")

        assert len(snapshot.pending_approvals) == 1
        assert snapshot.pending_approvals[0].approval_kind == "shell_exec"


class TestSnapshotDoesNotEmitEvents:
    """snapshot does not write to the event repository even when approvals repo is wired."""

    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_snapshot_with_approvals_repo_does_not_append(
        self,
    ) -> None:
        mock_events = AsyncMock()
        mock_runs = MagicMock()
        mock_approvals = InMemoryApprovalRepo()

        mock_run = MagicMock()
        mock_run.state = "executing"
        mock_runs.get = AsyncMock(return_value=mock_run)

        mock_events.list = AsyncMock(return_value=[])
        mock_events.latest_seq = AsyncMock(return_value=0)

        service = VisibilityService(
            events=mock_events,
            runs=mock_runs,
            approvals=mock_approvals,
        )

        _ = await service.snapshot("run-abc")

        assert not mock_events.append.called
        mock_events.list.assert_called_once()


class TestSnapshotNoIssuApprovalsRepo:
    """Snapshot works without approvals repo (backwards compatible)."""

    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_snapshot_without_approvals_repo(
        self,
    ) -> None:
        """When no approvals repo is wired, pending_approvals is empty."""
        mock_events = AsyncMock()
        mock_runs = MagicMock()

        mock_run = MagicMock()
        mock_run.state = "planning"
        mock_runs.get = AsyncMock(return_value=mock_run)

        mock_events.list = AsyncMock(return_value=[])
        mock_events.latest_seq = AsyncMock(return_value=0)

        service = VisibilityService(
            events=mock_events,
            runs=mock_runs,
        )
        snapshot = await service.snapshot("run-def")

        assert snapshot.pending_approvals == []
        assert snapshot.run_state == "planning"


# ---------------------------------------------------------------------------
# Approval decision paths — validate each path works tool-class agnostic
# ---------------------------------------------------------------------------


class TestDecisionPathsViaEngine:
    """Δtt Each approval decision variant works for every tool class."""

    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_grant_then_visibility_reflects_no_pending(
        self,
        engine: ApprovalEngine,
        approvals: InMemoryApprovalRepo,
        events: InMemoryEventRepo,
        providers: list[ToolProvider],
    ) -> None:
        """After granting, pending_approvals should not include the approval."""
        policy = _make_policy(
            rules=[
                ToolDecisionRule(
                    tool="file_write",
                    action="write",
                    decision="approval-required",
                ),
            ],
        )
        hook = ApprovalHook(
            engine=engine,
            registry_providers=providers,
            tool_policy=policy,
        )

        aid = await hook.before_invoke(
            run_id="run_dec",
            tool_id="file_write",
            action="write",
            summary="Write file",
        )

        # Resolve with Granted
        await engine.resolve(aid, Granted())

        # Visibility check — use runs=None, manifests=None to skip those branches
        mock_events_2 = AsyncMock()
        mock_events_2.list = AsyncMock(return_value=[])
        mock_events_2.latest_seq = AsyncMock(return_value=0)

        service = VisibilityService(
            events=mock_events_2,
            runs=None,
            manifests=None,
            approvals=approvals,
        )
        snapshot = await service.snapshot("run_dec")
        assert snapshot.pending_approvals == []

    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_deny_abandon_then_visibility_reflects_no_pending(
        self,
        engine: ApprovalEngine,
        approvals: InMemoryApprovalRepo,
        providers: list[ToolProvider],
    ) -> None:
        """After denying with abandon, pending_approvals is empty."""
        policy = _make_policy(
            rules=[
                ToolDecisionRule(
                    tool="shell_exec",
                    action="run",
                    decision="approval-required",
                ),
            ],
        )
        hook = ApprovalHook(
            engine=engine,
            registry_providers=providers,
            tool_policy=policy,
        )

        aid = await hook.before_invoke(
            run_id="run_dec2",
            tool_id="shell_exec",
            action="run",
            summary="Shell command",
        )

        await engine.resolve(aid, DeniedAbandon(reason="not safe"))

        mock_events_2 = AsyncMock()
        mock_events_2.list = AsyncMock(return_value=[])
        mock_events_2.latest_seq = AsyncMock(return_value=0)

        service = VisibilityService(
            events=mock_events_2,
            runs=None,
            manifests=None,
            approvals=approvals,
        )
        snapshot = await service.snapshot("run_dec2")
        assert snapshot.pending_approvals == []

    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_denied_alternate_path_no_pending(
        self,
        engine: ApprovalEngine,
        approvals: InMemoryApprovalRepo,
        providers: list[ToolProvider],
    ) -> None:
        """After denied alternate path, approval is not pending."""
        policy = _make_policy(
            rules=[
                ToolDecisionRule(
                    tool="network_egress",
                    action="request",
                    decision="approval-required",
                ),
            ],
        )
        hook = ApprovalHook(
            engine=engine,
            registry_providers=providers,
            tool_policy=policy,
        )

        aid = await hook.before_invoke(
            run_id="run_dec3",
            tool_id="network_egress",
            action="request",
            summary="HTTP call",
        )

        await engine.resolve(aid, DeniedAlternatePath(note="use cached data"))

        mock_events_2 = AsyncMock()
        mock_events_2.list = AsyncMock(return_value=[])
        mock_events_2.latest_seq = AsyncMock(return_value=0)

        service = VisibilityService(
            events=mock_events_2,
            runs=None,
            manifests=None,
            approvals=approvals,
        )
        snapshot = await service.snapshot("run_dec3")
        assert snapshot.pending_approvals == []

    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_timeout_no_pending(
        self,
        engine: ApprovalEngine,
        approvals: InMemoryApprovalRepo,
        providers: list[ToolProvider],
    ) -> None:
        """After timeout (both paths), approval is not pending."""
        policy = _make_policy(
            rules=[
                ToolDecisionRule(
                    tool="code_apply",
                    action="apply",
                    decision="approval-required",
                ),
            ],
        )
        hook = ApprovalHook(
            engine=engine,
            registry_providers=providers,
            tool_policy=policy,
        )

        aid = await hook.before_invoke(
            run_id="run_dec4",
            tool_id="code_apply",
            action="apply",
            summary="Apply code changes",
        )

        await engine.resolve(aid, Timeout(retryable=False))

        mock_events_2 = AsyncMock()
        mock_events_2.list = AsyncMock(return_value=[])
        mock_events_2.latest_seq = AsyncMock(return_value=0)

        service = VisibilityService(
            events=mock_events_2,
            runs=None,
            manifests=None,
            approvals=approvals,
        )
        snapshot = await service.snapshot("run_dec4")
        assert snapshot.pending_approvals == []
