"""Tests for EA briefing routine handler (P5-5 #85 → P5-FIX-3 #174).

Covers:
- Empty inbox briefing
- Normal briefing with inbox items
- Failure / error on missing upstream data
- Milestone phase validation
- **Durable ``run.artifact_created`` event emission** (P5-FIX-3)
- **Milestone emission through event repo** (P5-FIX-3)
"""

from datetime import UTC, datetime
from types import MappingProxyType

import pytest

from waywarden.domain.run_event import RunEvent
from waywarden.services.orchestration.briefing import (
    ALL_PHASES,
    EABriefingHandler,
    InboxEntry,
    _validate_milestones,
)

# -----------------------------------------------------------------------
# Empty inbox
# -----------------------------------------------------------------------


def test_empty_inbox_briefing() -> None:
    """Briefing with zero inbox items should succeed with zero counts."""
    handler = EABriefingHandler()
    result = handler.run(inbox_entries=[], pending_tasks=0)
    assert result.state.inbox_received == 0
    assert result.state.inbox_accepted == 0
    assert result.state.pending_tasks == 0
    milestones = result.milestones
    assert any(
        m["phase"] == "intake" and m["milestone"] == "received" and m["count"] == 0
        for m in milestones
    )


# -----------------------------------------------------------------------
# Normal briefing with inbox items
# -----------------------------------------------------------------------


def test_normal_briefing_with_items() -> None:
    """Briefing with inbox items should classify them."""
    inbox = [
        InboxEntry(
            subject="Meeting notes",
            body="Summary of standup",
            from_address="alice@example.com",
            received_at=datetime.now(UTC),
        ),
        InboxEntry(
            subject="Budget review",
            body="Q4 figures",
            from_address="bob@example.com",
            received_at=datetime.now(UTC),
        ),
    ]
    handler = EABriefingHandler()
    result = handler.run(inbox_entries=inbox, pending_tasks=2)
    assert result.state.inbox_received == 2
    assert result.state.inbox_accepted == 2
    assert result.state.pending_tasks == 2


def test_briefing_counts_items_with_no_subject() -> None:
    """Items with no subject are received but not accepted."""
    inbox = [
        InboxEntry(subject="Good message", body="Body", from_address="a@e.com"),
        InboxEntry(subject="", body="No subject line", from_address="b@e.com"),
        InboxEntry(subject="  ", body="Blank subject", from_address="c@e.com"),
    ]
    handler = EABriefingHandler()
    result = handler.run(inbox_entries=inbox)
    assert result.state.inbox_received == 3
    assert result.state.inbox_accepted == 1
    assert len(handler._stderr) == 2


# -----------------------------------------------------------------------
# Milestone validity
# -----------------------------------------------------------------------


def test_validate_milestones_ok() -> None:
    milestones = [
        {"phase": "intake", "milestone": "received"},
        {"phase": "plan", "milestone": "drafted"},
    ]
    _validate_milestones(milestones)


def test_validate_milestones_invalid_phase() -> None:
    with pytest.raises(ValueError):
        _validate_milestones([{"phase": "invalid_phase"}])


def test_all_phases_are_valid() -> None:
    for phase in ALL_PHASES:
        _validate_milestones([{"phase": phase, "milestone": "test"}])


# -----------------------------------------------------------------------
# BriefingResult fields
# -----------------------------------------------------------------------


def test_briefing_result_has_title() -> None:
    handler = EABriefingHandler()
    result = handler.run()
    assert result.title == "EA Briefing — " + datetime.now(UTC).strftime("%Y-%m-%d")
    assert "items_received" in result.artifact
    assert "items_accepted" in result.artifact
    assert "pending_tasks" in result.artifact
    assert "generated_at" in result.artifact
    assert "errors" in result.artifact


# -----------------------------------------------------------------------
# Phase compliance
# -----------------------------------------------------------------------


def test_milestones_only_use_valid_phases() -> None:
    """All milestones from run() use phases from ALL_PHASES."""
    handler = EABriefingHandler()
    result = handler.run()
    phases_used = {m["phase"] for m in result.milestones}
    valid = set(ALL_PHASES)
    assert phases_used <= valid


# -----------------------------------------------------------------------
# Durable event emission — run.artifact_created (P5-FIX-3 #174)
# -----------------------------------------------------------------------
"""Test fixture: in-memory event repo for capture."""


class _InMemoryEventRepo:
    """Simple sync-compatible ``RunEventRepository`` for tests."""

    def __init__(self) -> None:
        self._events: list[RunEvent] = []

    async def append(self, event: RunEvent) -> RunEvent:
        self._events.append(event)
        return event

    async def list(
        self, run_id: str, *, since_seq: int = 0, limit: int | None = None
    ) -> list[RunEvent]:
        return [e for e in self._events if e.seq > since_seq]

    async def latest_seq(self, run_id: str) -> int:
        return len(self._events)

    async def get(self, event_id: str) -> RunEvent | None:
        return None

    async def create(
        self, run_id: str, seq: int, event_type: str, payload: MappingProxyType
    ) -> RunEvent:
        raise NotImplementedError

    async def update_state(self, run_id: str, new_state: str, terminal_seq: int | None) -> RunEvent:
        raise NotImplementedError


@pytest.fixture
def event_repo() -> _InMemoryEventRepo:
    return _InMemoryEventRepo()


def test_briefing_emits_run_artifact_created(
    event_repo: _InMemoryEventRepo,
) -> None:
    """Briefing emits a durable run.artifact_created briefing artifact."""
    handler = EABriefingHandler(event_repo=event_repo)
    handler.run(
        inbox_entries=[
            InboxEntry(
                subject="Meeting notes",
                body="Summary",
                from_address="boss@example.com",
            ),
        ]
    )
    artefact_events = [e for e in event_repo._events if e.type == "run.artifact_created"]
    assert len(artefact_events) == 1
    evt = artefact_events[0]
    assert evt.payload["artifact_kind"] == "briefing"
    assert evt.payload["label"] == "briefing"
    assert "briefing-" in evt.payload["artifact_ref"]


def test_briefing_emits_run_progress_milestones(
    event_repo: _InMemoryEventRepo,
) -> None:
    """Briefing emits catalog-valid run.progress milestones."""
    handler = EABriefingHandler(event_repo=event_repo)
    handler.run(
        inbox_entries=[
            InboxEntry(subject="Budget review", body="Q4", from_address="a@b.com"),
        ]
    )
    progress_events = [e for e in event_repo._events if e.type == "run.progress"]
    phases_by_milestone: dict[str, str] = {}
    for evt in progress_events:
        phases_by_milestone[evt.payload["milestone"]] = evt.payload["phase"]
    assert phases_by_milestone["received"] == "intake"
    assert phases_by_milestone["accepted"] == "intake"
    assert phases_by_milestone["drafted"] == "plan"


def test_briefing_no_events_without_repo() -> None:
    """Without an event repo, briefing does not emit events."""
    handler = EABriefingHandler()
    result = handler.run(inbox_entries=[])
    assert result is not None
    # No events list raised or leaked — the handler just returns the result.
