"""Tests for EA handoff helper and delegation envelopes (P5-9 #89).

Covers:
- Envelope construction returns real DelegationEnvelope, not dict
- HandoffContext immutable frozen dataclass
- Handback checkpoints (plan-approved, implementation-complete, review-found-issues)
- Delegation widening validation (manifest narrowing)
- DelegationEnvelope frozen immutability
- HandbackRecord timestamp as datetime
- No new RT-002 event types introduced
"""

from datetime import datetime
from typing import Any, cast

import pytest

from waywarden.domain.delegation.envelope import DelegationEnvelope
from waywarden.domain.delegation.handoff import (
    VALID_CHECKPOINTS,
    EAAHandoffHelper,
    HandoffContext,
)
from waywarden.domain.ids import RunEventId, RunId
from waywarden.domain.manifest.manifest import WorkspaceManifest
from waywarden.domain.manifest.network_policy import NetworkPolicy
from waywarden.domain.manifest.secret_scope import SecretScope
from waywarden.domain.manifest.snapshot_policy import SnapshotPolicy
from waywarden.domain.manifest.tool_policy import ToolPolicy
from waywarden.domain.run_event import RunEvent
from waywarden.services.orchestration.milestones import is_valid_milestone


class _InMemoryEventRepo:
    def __init__(self) -> None:
        self._events: list[RunEvent] = []
        self._seqs: dict[str, int] = {}

    async def append(self, event: RunEvent) -> RunEvent:
        run_id = str(event.run_id)
        seq = self._seqs.get(run_id, 0) + 1
        confirmed = RunEvent(
            id=RunEventId(str(event.id)),
            run_id=RunId(run_id),
            seq=seq,
            type=event.type,
            payload=event.payload,
            timestamp=event.timestamp,
            causation=event.causation,
            actor=event.actor,
        )
        self._seqs[run_id] = seq
        self._events.append(confirmed)
        return confirmed

    async def list(
        self, run_id: str, *, since_seq: int = 0, limit: int | None = None
    ) -> list[RunEvent]:
        return [e for e in self._events if str(e.run_id) == run_id and e.seq > since_seq]

    async def latest_seq(self, run_id: str) -> int:
        return self._seqs.get(run_id, 0)


def _ctx(**kw: Any) -> HandoffContext:
    return HandoffContext(**kw)


# -----------------------------------------------------------------------
# Envelope construction — must return typed DelegationEnvelope
# -----------------------------------------------------------------------


def test_envelope_is_delegation_envelope() -> None:
    """make_envelope returns a real DelegationEnvelope, not a dict."""
    ctx = _ctx(
        objective="Write unit tests",
        constraints=("no network",),
        non_goals=("UI work",),
        acceptance_criteria=("all tests pass", "coverage > 80%"),
    )
    helper = EAAHandoffHelper(parent_run_id="run-x")
    env = helper.make_envelope_manual(ctx)
    assert isinstance(env, DelegationEnvelope)
    assert not isinstance(env, dict)  # regression: must not be a plain dict


def test_envelope_delegation_id_present() -> None:
    """DelegationEnvelope has a DelegationId property."""
    helper = EAAHandoffHelper(parent_run_id="run-x")
    env = helper.make_envelope_manual(_ctx(objective="Test"))
    assert hasattr(env, "id")
    assert env.id is not None


def test_envelope_parent_run_id() -> None:
    """The parent_run_id should match what was supplied."""
    helper = EAAHandoffHelper(parent_run_id="my-run-123")
    env = helper.make_envelope_manual(_ctx(objective="Test"))
    assert env.parent_run_id == "my-run-123"


def test_envelope_requires_context_first() -> None:
    """Calling make_envelope without build_context raises."""
    helper = EAAHandoffHelper()
    with pytest.raises(ValueError):
        helper.make_envelope()


def test_envelope_has_all_fields() -> None:
    """DelegationEnvelope carries all required typed fields."""
    ctx = _ctx(
        objective="Build this",
        constraints=("secure",),
        non_goals=("UI",),
        acceptance_criteria=("pass",),
    )
    helper = EAAHandoffHelper(parent_run_id="run-1")
    env = helper.make_envelope_manual(ctx)
    assert isinstance(env, DelegationEnvelope)
    assert env.brief.startswith("EA handoff: Build this")
    assert "Constraints:\n- secure" in env.brief
    assert "Non-goals:\n- UI" in env.brief
    assert "Acceptance criteria:\n- pass" in env.brief
    assert env.expected_outputs == ["artifact"]
    assert env.parent_run_id == "run-1"
    # child_manifest is a real type, not None
    assert env.child_manifest is not None


def test_envelope_with_custom_outputs() -> None:
    """Custom expected_outputs are passed through."""
    ctx = _ctx(objective="Build report")
    helper = EAAHandoffHelper()
    env = helper.make_envelope_manual(ctx, expected_outputs=["report.pdf", "summary.csv"])
    assert env.expected_outputs == ["report.pdf", "summary.csv"]


def test_envelope_includes_constraints_non_goals() -> None:
    """DelegationEnvelope carries constraints and non_goals from context."""
    ctx = _ctx(
        objective="Test",
        constraints=("no_network", "low_latency"),
        non_goals=("no_gui",),
    )
    helper = EAAHandoffHelper(parent_run_id="r1")
    env = helper.make_envelope_manual(ctx)
    assert "Constraints:\n- no_network\n- low_latency" in env.brief
    assert "Non-goals:\n- no_gui" in env.brief


# -----------------------------------------------------------------------
# HandoffContext immutability
# -----------------------------------------------------------------------


def test_handoff_context_is_frozen() -> None:
    """HandoffContext is a frozen dataclass."""
    ctx = _ctx(objective="Test", constraints=("secure",))
    assert isinstance(ctx, HandoffContext)
    assert ctx.constraints == ("secure",)
    # frozen=True means no __setattr__
    with pytest.raises((TypeError, AttributeError)):
        cast(Any, ctx).constraints = ()


# -----------------------------------------------------------------------
# Handback checkpoints
# -----------------------------------------------------------------------


def test_record_handback_plan_approved() -> None:
    helper = EAAHandoffHelper()
    record = helper.record_handback("plan-approved", "Scope agreed")
    assert record.checkpoint == "plan-approved"
    assert record.summary == "Scope agreed"
    assert len(helper.get_handback_records()) == 1


def test_record_handback_implemention_complete() -> None:
    helper = EAAHandoffHelper()
    record = helper.record_handback("implementation-complete", "Code written")
    assert record.checkpoint == "implementation-complete"
    assert len(helper.get_handback_records()) == 1


def test_record_handback_review_found_issues() -> None:
    helper = EAAHandoffHelper()
    record = helper.record_handback("review-found-issues", "Found bug")
    assert record.checkpoint == "review-found-issues"
    assert len(helper.get_handback_records()) == 1


def test_record_handback_multiple() -> None:
    helper = EAAHandoffHelper()
    helper.record_handback("plan-approved", "A")
    helper.record_handback("implementation-complete", "B")
    helper.record_handback("review-found-issues", "C")
    records = helper.get_handback_records()
    assert len(records) == 3
    assert records[0].checkpoint == "plan-approved"
    assert records[1].checkpoint == "implementation-complete"
    assert records[2].checkpoint == "review-found-issues"


def test_record_handback_valid_set() -> None:
    """VALID_CHECKPOINTS contains exactly the expected checkpoints."""
    assert {
        "plan-approved",
        "implementation-complete",
        "review-found-issues",
    } == VALID_CHECKPOINTS


def test_record_handback_invalid_raises() -> None:
    """Unknown checkpoints are rejected."""
    helper = EAAHandoffHelper()
    with pytest.raises(ValueError) as exc_info:
        helper.record_handback("unknown_type", "test")
    assert "unknown checkpoint" in str(exc_info.value)


def test_handback_has_timestamp_datetime() -> None:
    helper = EAAHandoffHelper()
    record = helper.record_handback("plan-approved", "")
    assert isinstance(record.timestamp, datetime)


def test_handback_record_is_frozen() -> None:
    """HandbackRecord is a frozen dataclass."""
    helper = EAAHandoffHelper()
    record = helper.record_handback("plan-approved", "test")
    with pytest.raises((TypeError, AttributeError)):
        cast(Any, record).checkpoint = "other"


# -----------------------------------------------------------------------
# Full handoff flow
# -----------------------------------------------------------------------


def test_full_handoff_flow() -> None:
    """End-to-end: build context → create envelope → record handbacks."""
    ctx = _ctx(objective="Refactor module X", acceptance_criteria=("no regressions",))
    helper = EAAHandoffHelper(parent_run_id="parent-1")
    env = helper.make_envelope_manual(ctx)
    assert isinstance(env, DelegationEnvelope)
    assert env.brief.startswith("EA handoff: Refactor module X")
    assert "Acceptance criteria:\n- no regressions" in env.brief
    helper.record_handback("plan-approved", "Phase scoped")
    helper.record_handback("implementation-complete", "PR merged")
    helper.record_handback("review-found-issues", "Edge case fix")
    assert len(helper.get_handback_records()) == 3
    assert helper.get_handback_records()[-1].checkpoint == "review-found-issues"


# -----------------------------------------------------------------------
# Children manifest — placeholder workflow
# -----------------------------------------------------------------------


def test_make_envelope_creates_child_manifest() -> None:
    """make_envelope constructs a child manifest even without a parent."""
    helper = EAAHandoffHelper(parent_run_id="run-x")
    helper.build_context("test")
    env = helper.make_envelope()
    assert isinstance(env, DelegationEnvelope)
    assert env.child_manifest is not None
    assert len(env.child_manifest.outputs) == 1


# -----------------------------------------------------------------------
# Delegation widening validation (P4-8 / #71)
# -----------------------------------------------------------------------


def test_narrow_manifest_raises_on_widening() -> None:
    """Narrowing should raise when child manifest widens authority."""
    from waywarden.domain.delegation.narrowing import narrow_manifest
    from waywarden.domain.manifest.network_policy import NetworkAllowRule

    parent_network = NetworkPolicy(mode="allowlist", allow=[], deny=[])
    parent_tool = ToolPolicy(preset="ask", rules=[], default_decision="approval-required")
    secret_scope = SecretScope(
        mode="brokered",
        allowed_secret_refs=[],
        mount_env=[],
        redaction_level="full",
    )
    snapshot_policy = SnapshotPolicy(
        on_start=False,
        on_completion=True,
        on_failure=True,
        before_destructive_actions=True,
        max_snapshots=1,
        include_paths=[],
        exclude_paths=[],
    )

    parent = WorkspaceManifest(
        run_id=RunId("par-1"),
        inputs=[],
        writable_paths=[],
        outputs=[],
        network_policy=parent_network,
        tool_policy=parent_tool,
        secret_scope=secret_scope,
        snapshot_policy=snapshot_policy,
    )
    widened_network = NetworkPolicy(
        mode="allowlist",
        allow=[NetworkAllowRule(host_pattern="github.com", scheme="https", purpose="widening")],
        deny=[],
    )
    widened_tool = ToolPolicy(preset="yolo", rules=[], default_decision="auto-allow")

    child = WorkspaceManifest(
        run_id=RunId("child-1"),
        inputs=[],
        writable_paths=[],
        outputs=[],
        network_policy=widened_network,
        tool_policy=widened_tool,  # widening from ask → yolo
        secret_scope=secret_scope,
        snapshot_policy=snapshot_policy,
    )
    with pytest.raises(RuntimeError) as exc_info:
        narrow_manifest(parent, child)
    assert "widens authority" in str(exc_info.value)


# -----------------------------------------------------------------------
# Regression: Dict-only envelope must fail
# -----------------------------------------------------------------------


def test_envelope_is_not_dict_only() -> None:
    """Regression: if EA handoff returns dict[str, Any], this test fails."""
    helper = EAAHandoffHelper()
    env = helper.make_envelope_manual(_ctx(objective="Test"))
    assert not isinstance(env, dict), "DelegationEnvelope must be a typed value, not a plain dict"
    assert type(env).__name__ == "DelegationEnvelope"


# -----------------------------------------------------------------------
# DelegationId / RunId presence
# -----------------------------------------------------------------------


def test_envelope_has_run_id_and_delegation_id_runtime_types() -> None:
    """DelegationEnvelope fields are ident types, not plain strings."""
    helper = EAAHandoffHelper(parent_run_id="custom-parent-456")
    env = helper.make_envelope_manual(_ctx(objective="Test"))
    # The DelegationId and RunId are NewType(str) which behave like strings
    # at runtime — assert the envelope stores them
    assert env.parent_run_id == "custom-parent-456"
    assert env.id is not None  # exists


@pytest.mark.asyncio
async def test_record_handback_async_uses_catalog_valid_progress_event() -> None:
    events = _InMemoryEventRepo()
    helper = EAAHandoffHelper(parent_run_id="parent-1", events=events)
    helper.make_envelope_manual(_ctx(objective="Build", constraints=("no network",)))

    await helper.record_handback_async("plan-approved", "Plan approved")

    assert len(events._events) == 1
    event = events._events[0]
    assert event.type == "run.progress"
    assert is_valid_milestone(str(event.payload["phase"]), str(event.payload["milestone"]))
    assert event.payload["phase"] == "handoff"
    assert event.payload["milestone"] == "envelope_emitted"
    assert event.payload["checkpoint"] == "plan-approved"
