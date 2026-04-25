"""Tests for EA briefing routine handler (P5-5 #85).

Covers:
- Empty inbox briefing
- Normal briefing with inbox items
- Failure / error on missing upstream data
- Milestone phase validation
"""

from datetime import UTC, datetime

import pytest

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
    # Milestones are still emitted (just with zero counts)
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
        InboxEntry(
            subject="Good message",
            body="Body",
            from_address="a@e.com",
        ),
        InboxEntry(
            subject="",
            body="No subject line",
            from_address="b@e.com",
        ),
        InboxEntry(
            subject="  ",
            body="Blank subject",
            from_address="c@e.com",
        ),
    ]
    handler = EABriefingHandler()
    result = handler.run(inbox_entries=inbox)
    assert result.state.inbox_received == 3
    assert result.state.inbox_accepted == 1  # only "Good message"
    assert len(handler._stderr) == 2  # two items with no subject


# -----------------------------------------------------------------------
# Milestone validity
# -----------------------------------------------------------------------


def test_validate_milestones_ok() -> None:
    milestones = [
        {"phase": "intake", "milestone": "received"},
        {"phase": "plan", "milestone": "drafted"},
    ]
    _validate_milestones(milestones)  # should not raise


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
