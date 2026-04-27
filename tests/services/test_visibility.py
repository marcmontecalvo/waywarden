"""Tests for VisibilityService — read-only snapshot of run progress."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from waywarden.domain.ids import RunEventId, RunId
from waywarden.domain.run_event import RunEvent
from waywarden.services.visibility import VisibilityService


@pytest.fixture(autouse=True)
def _utc_now() -> datetime:
    """Fixed timestamp for determinism."""
    return datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)


class TestSnapshotReflectsProgressEvents:
    """snapshot(run_id) returns run state plus every run.progress event."""

    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_snapshot_reflects_progress_events(self) -> None:
        """Events emitted to the repo are reflected in the snapshot's milestones list."""
        mock_events = AsyncMock()
        mock_runs = MagicMock()

        mock_run = MagicMock()
        mock_run.state = "executing"
        mock_runs.get = AsyncMock(return_value=mock_run)

        now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        progress_event_1 = RunEvent(
            id=RunEventId("evt-1"),
            run_id=RunId("run-abc"),
            seq=1,
            type="run.progress",
            payload={"phase": "intake", "milestone": "received"},
            timestamp=now,
            causation=None,
            actor=None,
        )
        progress_event_2 = RunEvent(
            id=RunEventId("evt-2"),
            run_id=RunId("run-abc"),
            seq=2,
            type="run.progress",
            payload={"phase": "plan", "milestone": "drafted"},
            timestamp=now,
            causation=None,
            actor=None,
        )

        mock_events.list = AsyncMock(return_value=[progress_event_1, progress_event_2])
        mock_events.latest_seq = AsyncMock(return_value=2)

        service = VisibilityService(events=mock_events, runs=mock_runs)
        snapshot = await service.snapshot("run-abc")

        assert snapshot.run_state == "executing"
        assert len(snapshot.milestones) == 2
        assert snapshot.milestones[0].phase == "intake"
        assert snapshot.milestones[0].milestone == "received"
        assert snapshot.milestones[0].seq == 1
        assert snapshot.milestones[1].phase == "plan"
        assert snapshot.milestones[1].milestone == "drafted"
        assert snapshot.milestones[1].seq == 2
        assert snapshot.milestones[1].description == "Initial plan drafted"
        assert len(snapshot.artifacts) == 0


class TestSnapshotDoesNotEmitEvents:
    """snapshot does not write to the event repository."""

    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_snapshot_does_not_emit_events(self) -> None:
        """Calling snapshot does not increase the event count on the repo."""
        mock_events = AsyncMock()
        mock_runs = MagicMock()

        mock_run = MagicMock()
        mock_run.state = "planning"
        mock_runs.get = AsyncMock(return_value=mock_run)

        now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        progress_event = RunEvent(
            id=RunEventId("evt-1"),
            run_id=RunId("run-abc"),
            seq=1,
            type="run.progress",
            payload={"phase": "intake", "milestone": "accepted"},
            timestamp=now,
            causation=None,
            actor=None,
        )

        mock_events.list = AsyncMock(return_value=[progress_event])
        mock_events.latest_seq = AsyncMock(return_value=1)

        service = VisibilityService(events=mock_events, runs=mock_runs)

        initial_event_count = await mock_events.latest_seq("run-abc")
        _ = await service.snapshot("run-abc")
        final_event_count = await mock_events.latest_seq("run-abc")

        assert initial_event_count == final_event_count == 1
        mock_events.list.assert_called_once()
        # append must never be called on the event repo
        assert not mock_events.append.called


class TestMilestonesMatchCatalog:
    """Every milestone.phase and milestone.milestone appears in the milestone catalog."""

    @pytest.mark.anyio
    async def test_milestones_match_catalog(self) -> None:
        """Only catalog-declared phase/milestone pairs appear in the snapshot."""
        from waywarden.services.orchestration.milestones import MILESTONE_CATALOG
        from waywarden.services.visibility import _MILESTONE_DESCRIPTION_MAP

        # Build expected keys from the canonical milestone catalog
        expected_keys: set[tuple[str, str]] = {(md.phase, md.milestone) for md in MILESTONE_CATALOG}

        actual_keys = set(_MILESTONE_DESCRIPTION_MAP.keys())
        assert actual_keys == expected_keys


class TestSnapshotOnlyProgressEvents:
    @pytest.mark.anyio
    async def test_snapshot_filters_only_progress_events(self) -> None:
        """Non progress events are skipped in milestones list."""
        mock_events = AsyncMock()
        mock_runs = MagicMock()

        mock_run = MagicMock()
        mock_run.state = "executing"
        mock_runs.get = AsyncMock(return_value=mock_run)

        now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        events = [
            RunEvent(
                id=RunEventId("evt-1"),
                run_id=RunId("run-x"),
                seq=1,
                type="run.created",
                payload={
                    "instance_id": "inst-1",
                    "profile": "ea",
                    "policy_preset": "ask",
                    "manifest_ref": "//manifest/1",
                    "entrypoint": "api",
                },
                timestamp=now,
                causation=None,
                actor=None,
            ),
            RunEvent(
                id=RunEventId("evt-2"),
                run_id=RunId("run-x"),
                seq=2,
                type="run.progress",
                payload={"phase": "execute", "milestone": "tool_invoked"},
                timestamp=now,
                causation=None,
                actor=None,
            ),
            RunEvent(
                id=RunEventId("evt-3"),
                run_id=RunId("run-x"),
                seq=3,
                type="run.completed",
                payload={"outcome": "success"},
                timestamp=now,
                causation=None,
                actor=None,
            ),
        ]

        mock_events.list = AsyncMock(return_value=events)
        mock_events.latest_seq = AsyncMock(return_value=3)

        service = VisibilityService(events=mock_events, runs=mock_runs)
        snapshot = await service.snapshot("run-x")

        # Only progress events become milestones
        assert len(snapshot.milestones) == 1
        assert snapshot.milestones[0].phase == "execute"
        assert snapshot.milestones[0].milestone == "tool_invoked"
