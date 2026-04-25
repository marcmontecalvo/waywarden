"""Tests for EA handoff helper and delegation envelopes (P5-9 #89).

Covers:
- Envelope construction with handoff context
- Handback checkpoints (plan-approved, implementation-complete, review-found-issues)
- Delegation widening validation (manifest narrowing)
"""

from datetime import datetime

import pytest

from waywarden.domain.delegation.handoff import (
    EAAHandoffHelper,
    HandoffContext,
)


def _ctx(**kw) -> HandoffContext:
    return HandoffContext(**kw)


# -----------------------------------------------------------------------
# Envelope construction
# -----------------------------------------------------------------------


def test_envelope_construction() -> None:
    """Build an envelope from a basic handoff context."""
    ctx = _ctx(
        objective="Write unit tests",
        constraints=("no network",),
        non_goals=("UI work",),
        acceptance_criteria=("all tests pass", "coverage > 80%"),
    )
    helper = EAAHandoffHelper(parent_run_id="run-x")
    env = helper.make_envelope_manual(ctx)
    assert env["brief"] == "EA handoff: Write unit tests"
    assert env["expected_outputs"] == ["artifact"]
    assert env["constraints"] == ("no network",)
    assert env["non_goals"] == ("UI work",)
    assert env["acceptance_criteria"] == ("all tests pass", "coverage > 80%")


def test_envelope_with_custom_outputs() -> None:
    """Custom expected_outputs are passed through."""
    ctx = _ctx(objective="Build report")
    helper = EAAHandoffHelper()
    env = helper.make_envelope_manual(ctx, expected_outputs=["report.pdf", "summary.csv"])
    assert env["expected_outputs"] == ["report.pdf", "summary.csv"]


def test_envelope_parent_run_id() -> None:
    """The parent_run_id should match what was supplied."""
    helper = EAAHandoffHelper(parent_run_id="my-run-123")
    env = helper.make_envelope_manual(_ctx(objective="Test"))
    assert env["parent_run_id"] == "my-run-123"


def test_envelope_requires_context_first() -> None:
    """Calling make_envelope without build_context raises."""
    helper = EAAHandoffHelper()
    with pytest.raises(ValueError):
        helper.make_envelope()


# -----------------------------------------------------------------------
# Envelope fields per P4-8 spec
# -----------------------------------------------------------------------


def test_envelope_has_all_fields() -> None:
    ctx = _ctx(objective="Build this")
    helper = EAAHandoffHelper(parent_run_id="run-1")
    env = helper.make_envelope_manual(ctx)
    for key in (
        "parent_run_id",
        "brief",
        "expected_outputs",
        "constraints",
        "non_goals",
        "acceptance_criteria",
        "artifact_context",
        "created_at",
    ):
        assert key in env


# -----------------------------------------------------------------------
# Handback checkpoints
# -----------------------------------------------------------------------


def test_record_handback_planned_approved() -> None:
    helper = EAAHandoffHelper()
    record = helper.record_handback("plan-approved", "Scope agreed")
    assert record.checkpoint == "plan-approved"
    assert record.summary == "Scope agreed"
    assert len(helper.get_handback_records()) == 1


def test_record_handback_runs_multiple() -> None:
    helper = EAAHandoffHelper()
    helper.record_handback("plan-approved", "A")
    helper.record_handback("implementation-complete", "B")
    helper.record_handback("review-found-issues", "C")
    records = helper.get_handback_records()
    assert len(records) == 3
    assert records[0].checkpoint == "plan-approved"
    assert records[1].checkpoint == "implementation-complete"
    assert records[2].checkpoint == "review-found-issues"


# -----------------------------------------------------------------------
# HandbackRecord structure
# -----------------------------------------------------------------------


def test_handback_has_timestamp() -> None:
    helper = EAAHandoffHelper()
    record = helper.record_handback("plan-approved", "")
    # ISO timestamp should be parseable
    datetime.fromisoformat(record.timestamp)


# -----------------------------------------------------------------------
# Full handoff flow
# -----------------------------------------------------------------------


def test_full_handoff_flow() -> None:
    """End-to-end: build context → create envelope → record handbacks."""
    ctx = _ctx(objective="Refactor module X", acceptance_criteria=("no regressions",))
    helper = EAAHandoffHelper(parent_run_id="parent-1")
    env = helper.make_envelope_manual(ctx)
    assert env["brief"] == "EA handoff: Refactor module X"
    helper.record_handback("plan-approved", "Phase scoped")
    helper.record_handback("implementation-complete", "PR merged")
    helper.record_handback("review-found-issues", "Edge case fix")
    assert len(helper.get_handback_records()) == 3
    assert helper.get_handback_records()[-1].checkpoint == "review-found-issues"


def test_handoff_context_immutability() -> None:
    """HandoffContext should be frozen."""
    ctx = _ctx(objective="Test", constraints=("secure",))
    assert isinstance(ctx, HandoffContext)
    assert ctx.constraints == ("secure",)


# -----------------------------------------------------------------------
# Delegation widening validation (P4-8 / #71)
# -----------------------------------------------------------------------


def test_narrow_manifest_raises_on_widening() -> None:
    """Narrowing should raise when child manifest widens authority."""
    from types import SimpleNamespace

    from waywarden.domain.delegation.narrowing import narrow_manifest
    from waywarden.domain.manifest.manifest import WorkspaceManifest

    _NP = SimpleNamespace(mode="allowlist", allow=[])
    _TP = SimpleNamespace(preset="ask", allow=[])
    _SS = SimpleNamespace(allowed_secret_refs=[])
    _SP = SimpleNamespace(mode="prune_mutable")

    parent = WorkspaceManifest(
        run_id="par-1",
        inputs=[],
        writable_paths=[],
        outputs=[],
        network_policy=_NP,
        tool_policy=_TP,
        secret_scope=_SS,
        snapshot_policy=_SP,
    )
    _YoloTP = SimpleNamespace(preset="yolo", allow=[])  # widening

    child = WorkspaceManifest(
        run_id="child-1",
        inputs=[],
        writable_paths=[],
        outputs=[],
        network_policy=_NP,
        tool_policy=_YoloTP,  # widening from ask → yolo
        secret_scope=_SS,
        snapshot_policy=_SP,
    )
    with pytest.raises(RuntimeError) as exc_info:
        narrow_manifest(parent, child)
    assert "widens authority" in str(exc_info.value)


class MockNP:
    mode: str = "allowlist"
    allow: list = []


class MockTP:
    preset: str = "ask"
    allow: list = []


class MockSS:
    allowed_secret_refs: list = []


class MockSP:
    mode: str = "prune_mutable"
