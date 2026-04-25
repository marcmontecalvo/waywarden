"""Tests for EA task service covering grant / deny-abandon / deny-alternate / timeout (P5-4 #84)."""

import pytest

from waywarden.services.approval_types import (
    ApprovalAlreadyResolvedError,
    DeniedAbandon,
    DeniedAlternatePath,
    Granted,
    Timeout,
)
from waywarden.services.ea_task_service import (
    ApprovalDecisionRequest,
    CreateTaskRequest,
    EATaskService,
    RequestApprovalRequest,
    TransitionTaskRequest,
)

# -----------------------------------------------------------------------
# Task creation
# -----------------------------------------------------------------------


def test_create_task_emits_event() -> None:
    svc = EATaskService()
    task = svc.create_task(
        CreateTaskRequest(
            session_id="s1",
            title="Test",
            objective="Do stuff",
            acceptance_criteria=("c1",),
        )
    )
    assert task["state"] == "draft"
    assert task["session_id"] == "s1"
    events = svc.get_events()
    assert len(events) == 1
    assert events[0]["type"] == "run.progress"
    assert events[0]["payload"]["phase"] == "task_created"


# -----------------------------------------------------------------------
# Task transitions
# -----------------------------------------------------------------------


def test_transition_draft_to_planning() -> None:
    svc = EATaskService()
    task = svc.create_task(CreateTaskRequest(session_id="s1", title="T", objective="O"))
    result = svc.transition_task(TransitionTaskRequest(task_id=task["id"], state="planning"))
    assert result["state"] == "planning"
    events = svc.get_events()
    assert any(e["payload"]["phase"] == "task_transitioned" for e in events)


def test_transition_executing_to_waiting_approval() -> None:
    svc = EATaskService()
    task = svc.create_task(CreateTaskRequest(session_id="s1", title="T", objective="O"))
    svc.transition_task(TransitionTaskRequest(task_id=task["id"], state="planning"))
    svc.transition_task(TransitionTaskRequest(task_id=task["id"], state="executing"))
    result = svc.transition_task(
        TransitionTaskRequest(task_id=task["id"], state="waiting_approval")
    )
    assert result["state"] == "waiting_approval"


def test_transition_completed_is_forbidden() -> None:
    svc = EATaskService()
    task = svc.create_task(CreateTaskRequest(session_id="s1", title="T", objective="O"))
    with pytest.raises(ValueError):
        svc.transition_task(TransitionTaskRequest(task_id=task["id"], state="completed"))


def test_transition_nonexistent_task_raises() -> None:
    svc = EATaskService()
    with pytest.raises(KeyError):
        svc.transition_task(TransitionTaskRequest(task_id="nonexistent", state="planning"))


# -----------------------------------------------------------------------
# Approval — grant
# -----------------------------------------------------------------------


def test_request_approval_emits_waiting_event() -> None:
    svc = EATaskService()
    task = svc.create_task(CreateTaskRequest(session_id="s1", title="T", objective="O"))
    svc.transition_task(TransitionTaskRequest(task_id=task["id"], state="planning"))
    svc.transition_task(TransitionTaskRequest(task_id=task["id"], state="executing"))
    svc.request_approval(RequestApprovalRequest(task_id=task["id"]))
    events = svc.get_events()
    assert any(e["type"] == "run.approval_waiting" for e in events)


def test_grant_approval_resolves_to_planning() -> None:
    svc = EATaskService()
    task = svc.create_task(CreateTaskRequest(session_id="s1", title="T", objective="O"))
    svc.transition_task(TransitionTaskRequest(task_id=task["id"], state="planning"))
    svc.transition_task(TransitionTaskRequest(task_id=task["id"], state="executing"))
    svc.request_approval(RequestApprovalRequest(task_id=task["id"]))
    result = svc.resolve_approval(ApprovalDecisionRequest(task_id=task["id"], decision=Granted()))
    assert result["state"] == "granted"
    events = svc.get_events()
    assert any(e["type"] == "run.plan_ready" for e in events)


# -----------------------------------------------------------------------
# Approval — deny-abandon
# -----------------------------------------------------------------------


def test_deny_abandon_resolves_to_cancelled() -> None:
    svc = EATaskService()
    task = svc.create_task(CreateTaskRequest(session_id="s1", title="T", objective="O"))
    svc.transition_task(TransitionTaskRequest(task_id=task["id"], state="planning"))
    svc.transition_task(TransitionTaskRequest(task_id=task["id"], state="executing"))
    svc.request_approval(RequestApprovalRequest(task_id=task["id"]))
    result = svc.resolve_approval(
        ApprovalDecisionRequest(task_id=task["id"], decision=DeniedAbandon(reason="skip"))
    )
    assert result["state"] == "denied_abandon"
    events = svc.get_events()
    assert any(e["type"] == "run.cancelled" for e in events)


# -----------------------------------------------------------------------
# Approval — deny-alternate
# -----------------------------------------------------------------------


def test_deny_alternate_path_resolves_with_note() -> None:
    svc = EATaskService()
    task = svc.create_task(CreateTaskRequest(session_id="s1", title="T", objective="O"))
    svc.transition_task(TransitionTaskRequest(task_id=task["id"], state="planning"))
    svc.transition_task(TransitionTaskRequest(task_id=task["id"], state="executing"))
    svc.request_approval(RequestApprovalRequest(task_id=task["id"]))
    result = svc.resolve_approval(
        ApprovalDecisionRequest(
            task_id=task["id"],
            decision=DeniedAlternatePath(note="use-alternative"),
        )
    )
    assert result["state"] == "denied_alternate_path"
    events = svc.get_events()
    # deny-alternate maps to run.progress
    assert any(e["type"] == "run.progress" and "alternate_path" in e["payload"] for e in events)


# -----------------------------------------------------------------------
# Approval — timeout
# -----------------------------------------------------------------------


def test_timeout_resolves_to_cancelled() -> None:
    svc = EATaskService()
    task = svc.create_task(CreateTaskRequest(session_id="s1", title="T", objective="O"))
    svc.transition_task(TransitionTaskRequest(task_id=task["id"], state="planning"))
    svc.transition_task(TransitionTaskRequest(task_id=task["id"], state="executing"))
    svc.request_approval(RequestApprovalRequest(task_id=task["id"]))
    result = svc.resolve_approval(
        ApprovalDecisionRequest(task_id=task["id"], decision=Timeout(retryable=True))
    )
    assert result["state"] == "timeout"
    events = svc.get_events()
    assert any(e["type"] == "run.cancelled" for e in events)


# -----------------------------------------------------------------------
# Already resolved approvals are rejected
# -----------------------------------------------------------------------


def test_resolve_already_resolved_approval_raises() -> None:
    svc = EATaskService()
    task = svc.create_task(CreateTaskRequest(session_id="s1", title="T", objective="O"))
    svc.transition_task(TransitionTaskRequest(task_id=task["id"], state="planning"))
    svc.transition_task(TransitionTaskRequest(task_id=task["id"], state="executing"))
    svc.request_approval(RequestApprovalRequest(task_id=task["id"]))
    svc.resolve_approval(ApprovalDecisionRequest(task_id=task["id"], decision=Granted()))
    with pytest.raises(ApprovalAlreadyResolvedError):
        svc.resolve_approval(
            ApprovalDecisionRequest(task_id=task["id"], decision=DeniedAbandon(reason="double"))
        )


# -----------------------------------------------------------------------
# Request approval on missing task raises
# -----------------------------------------------------------------------


def test_request_approval_on_missing_task_raises() -> None:
    svc = EATaskService()
    with pytest.raises(KeyError):
        svc.request_approval(RequestApprovalRequest(task_id="nonexistent"))


# -----------------------------------------------------------------------
# RT-002 event assertions
# -----------------------------------------------------------------------


def test_full_event_stream_assertion() -> None:
    """End-to-end: create -> planning -> executing -> approve -> grant -> transition."""
    svc = EATaskService()
    task = svc.create_task(CreateTaskRequest(session_id="s1", title="Build", objective="Ship it"))
    assert task["state"] == "draft"
    svc.transition_task(TransitionTaskRequest(task_id=task["id"], state="planning"))
    svc.transition_task(TransitionTaskRequest(task_id=task["id"], state="executing"))
    svc.request_approval(RequestApprovalRequest(task_id=task["id"]))
    svc.resolve_approval(ApprovalDecisionRequest(task_id=task["id"], decision=Granted()))
    svc.transition_task(TransitionTaskRequest(task_id=task["id"], state="planning"))
    svc.transition_task(TransitionTaskRequest(task_id=task["id"], state="executing"))
    svc.transition_task(TransitionTaskRequest(task_id=task["id"], state="completed"))
    events = svc.get_events()
    assert any(e["type"] == "run.progress" for e in events)
    assert any(e["type"] == "run.approval_waiting" for e in events)
    assert any(e["type"] == "run.plan_ready" for e in events)
