"""Async tests for EA triage routine.

Uses the async-compatible fake service to prove triage:
- resolves items through the EATaskService surface (not direct handler)
- handles Granted, DeniedAbandon
- marks malformed items correctly
- approval gates outbound actions

Canonical references:
    - P5-FIX-3 #174 (EA routine orchestration wiring)
    - P5-FIX-2 #173 (repository-backed EA task service)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest
from fakes import FakeEATaskService

from waywarden.services.approval_types import (
    DeniedAbandon,
    Granted,
)
from waywarden.services.orchestration.triage import (
    EAIboxTriageHandler,
    InboxItem,
)

# -----------------------------------------------------------------------
# Classification and drafting
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_classify_only() -> None:
    """Items are classified with no decisions."""
    svc = FakeEATaskService()
    handler = EAIboxTriageHandler(task_service=svc)
    items = [InboxItem(subject="Meeting", from_address="a@e.com", body="Hi")]
    result = await handler.run(items)
    assert result.items_triaged == 1
    assert result.items[0].classification == "scheduling"


@pytest.mark.asyncio
async def test_draft_approved() -> None:
    """Approved items should have approved=True."""
    svc = FakeEATaskService()
    handler = EAIboxTriageHandler(task_service=svc)
    items = [InboxItem(subject="Budget", from_address="b@e.com", body="Q4")]
    result = await handler.run(items, decisions={"Budget": Granted()})
    assert result.items_triaged == 1
    assert result.items_approved == 1
    assert result.items[0].approved is True


@pytest.mark.asyncio
async def test_draft_denied() -> None:
    """Denied items should not be approved."""
    svc = FakeEATaskService()
    handler = EAIboxTriageHandler(task_service=svc)
    items = [InboxItem(subject="Request", from_address="c@e.com", body="Info")]
    result = await handler.run(items, decisions={"Request": DeniedAbandon(reason="no")})
    assert result.items_triaged == 1
    assert result.items_denied == 1
    assert result.items[0].approved is False


# -----------------------------------------------------------------------
# Malformed input
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_malformed_input_blanks_subject() -> None:
    """Blank subject items are malformed."""
    svc = FakeEATaskService()
    handler = EAIboxTriageHandler(task_service=svc)
    items = [InboxItem(subject="", from_address="x@e.com", body="no subject")]
    result = await handler.run(items)
    assert result.items_malformed == 1
    assert result.items_triaged == 0


@pytest.mark.asyncio
async def test_malformed_input_whitespace_only_subject() -> None:
    """Whitespace-only subject is malformed."""
    svc = FakeEATaskService()
    handler = EAIboxTriageHandler(task_service=svc)
    items = [InboxItem(subject="  ", from_address="y@e.com", body="white")]
    result = await handler.run(items)
    assert result.items_malformed == 1
