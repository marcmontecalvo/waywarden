"""Tests for EA routine execution surface (P5-FIX-3 #174).

Proves:
- Routine slices are resolved from EA-hydrated resolved_assets
- EACoroutine returns the expected artifact kinds for known routine IDs
- Event emission passes through the correct kinds
"""

import pytest

from waywarden.services.orchestration.briefing import BriefingResult, InboxEntry
from waywarden.services.orchestration.routine import EACoroutine

# -----------------------------------------------------------------------
# Mock assets
# -----------------------------------------------------------------------


class _MockAsset:
    """Minimal stand-in for AssetMetadata in tests."""

    def __init__(
        self,
        id: str,
        kind: str,
        milestones: list[dict[str, object]] | None = None,
        emits_events: tuple[str, ...] = (),
    ) -> None:
        self.id = id
        self.kind = kind
        self.milestones = milestones or []
        self.emits_events = emits_events


def test_resolve_routine_slices_filters_by_kind() -> None:
    """Only routine-kind assets are returned."""
    coro = EACoroutine()
    assets = [
        _MockAsset(id="ea-briefing", kind="routine"),
        _MockAsset(id="dashboard", kind="widget"),
        _MockAsset(id="strict-policy", kind="policy"),
        _MockAsset(id="ea-scheduler", kind="routine"),
    ]
    slices = coro.resolve_routine_slices(assets)
    assert len(slices) == 2
    assert slices[0].asset_id == "ea-briefing"
    assert slices[1].asset_id == "ea-scheduler"


def test_routine_slice_populates_from_asset_metadata() -> None:
    """RoutineSlice captures milestones and emits events."""
    coro = EACoroutine()
    asset = _MockAsset(
        id="ea-briefing",
        kind="routine",
        milestones=[{"phase": "intake", "names": ["received"]}],
        emits_events=("run.progress", "run.artifact_created"),
    )
    slices = coro.resolve_routine_slices([asset])
    assert len(slices) == 1
    slice_ = slices[0]
    assert slice_.asset_id == "ea-briefing"
    assert len(slice_.milestone_specs) == 1
    assert "run.progress" in slice_.emits_events
    assert "run.artifact_created" in slice_.emits_events


def test_artifact_kind_inference() -> None:
    """Routine slices infer correct artifact kinds from asset id."""
    coro = EACoroutine()
    assert coro.briefing_artifact_kind() == "briefing"


def test_scheduler_emit_events() -> None:
    """Scheduler declares expected events."""
    coro = EACoroutine()
    events = coro.scheduler_emit_events()
    assert "run.progress" in events


def test_triage_emit_events() -> None:
    """Triage declares expected events."""
    coro = EACoroutine()
    events = coro.triage_emit_events()
    assert "run.progress" in events


@pytest.mark.asyncio
async def test_execute_requires_resolved_routine_asset() -> None:
    coro = EACoroutine()
    with pytest.raises(ValueError, match="was not resolved"):
        await coro.execute("ea-briefing", [])


@pytest.mark.asyncio
async def test_execute_dispatches_briefing_routine() -> None:
    coro = EACoroutine()
    result = await coro.execute(
        "ea-briefing",
        [_MockAsset(id="ea-briefing", kind="routine")],
        inbox_entries=[InboxEntry(subject="Daily", body="Body", from_address="a@example.com")],
    )

    assert isinstance(result, BriefingResult)
    assert result.state.inbox_received == 1
