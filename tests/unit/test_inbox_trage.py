"""Tests for EA inbox triage routine (P5-7 #87)."""

from waywarden.services.approval_types import (
    DeniedAbandon,
    Granted,
)
from waywarden.services.ea_task_service import EATaskService
from waywarden.services.orchestration.triage import (
    EAIboxTriageHandler,
    InboxItem,
    TriageResult,
)

# -----------------------------------------------------------------------
# Classify-only
# -----------------------------------------------------------------------


def test_classify_only():
    """Items are classified with no decisions."""
    svc = EATaskService()
    handler = EAIboxTriageHandler(task_service=svc)
    items = [InboxItem(subject="Meeting", from_address="a@e.com", body="Hi")]
    result = handler.run(items)
    assert result.items_triaged == 1
    assert result.items[0].classification == "scheduling"


# -----------------------------------------------------------------------
# Draft approved
# -----------------------------------------------------------------------


def test_draft_approved():
    """Approved items should have approved=True."""
    svc = EATaskService()
    handler = EAIboxTriageHandler(task_service=svc)
    items = [InboxItem(subject="Budget", from_address="b@e.com", body="Q4")]
    result = handler.run(items, decisions={"Budget": Granted()})
    assert result.items_triaged == 1
    assert result.items_approved == 1
    assert result.items[0].approved is True


# -----------------------------------------------------------------------
# Draft denied
# -----------------------------------------------------------------------


def test_draft_denied():
    """Denied items should not be approved."""
    svc = EATaskService()
    handler = EAIboxTriageHandler(task_service=svc)
    items = [InboxItem(subject="Request", from_address="c@e.com", body="Info")]
    result = handler.run(items, decisions={"Request": DeniedAbandon(reason="no")})
    assert result.items_triaged == 1
    assert result.items_denied == 1
    assert result.items[0].approved is False


# -----------------------------------------------------------------------
# Malformed input
# -----------------------------------------------------------------------


def test_malformed_input_blanks_subject():
    """Blank subject items are malformed."""
    svc = EATaskService()
    handler = EAIboxTriageHandler(task_service=svc)
    items = [InboxItem(subject="", from_address="x@e.com", body="no subject")]
    result = handler.run(items)
    assert result.items_malformed == 1
    assert result.items_triaged == 0


def test_malformed_input_whitespace_only_subject():
    """Whitespace-only subject is malformed."""
    svc = EATaskService()
    handler = EAIboxTriageHandler(task_service=svc)
    items = [InboxItem(subject="  ", from_address="y@e.com", body="white")]
    result = handler.run(items)
    assert result.items_malformed == 1


def test_ea_inbox_triage_empty_items():
    """No items is valid."""
    svc = EATaskService()
    handler = EAIboxTriageHandler(task_service=svc)
    result = handler.run([])
    assert result.items_triaged == 0


def test_ea_inbox_triage_result_type():
    """Return should be TriageResult."""
    svc = EATaskService()
    handler = EAIboxTriageHandler(task_service=svc)
    result = handler.run([])
    assert isinstance(result, TriageResult)


def test_drafted_response_contains_keywords():
    """Drafted response should include subject and category."""
    svc = EATaskService()
    handler = EAIboxTriageHandler(task_service=svc)
    items = [InboxItem(subject="Meeting", from_address="a@e.com", body="Hi")]
    result = handler.run(items)
    assert len(result.items) == 1
    assert "Meeting" in result.items[0].drafted_response
    assert "scheduling" in result.items[0].drafted_response


def test_multiple_items_mixed_outcomes():
    """Multiple items with mixed classification and decisions."""
    svc = EATaskService()
    handler = EAIboxTriageHandler(task_service=svc)
    items = [
        InboxItem(subject="Meeting", from_address="1@e.com", body="a"),
        InboxItem(subject="  ", from_address="2@e.com", body="b"),
        InboxItem(subject="Budget", from_address="3@e.com", body="c"),
    ]
    result = handler.run(
        items,
        decisions={"Meeting": Granted(), "Budget": DeniedAbandon(reason="no")},
    )
    assert result.items_triaged == 2
    assert result.items_malformed == 1
    assert result.items_approved == 1
    assert result.items_denied == 1
