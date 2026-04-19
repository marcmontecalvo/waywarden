from datetime import UTC, datetime, timedelta, timezone

import pytest

from waywarden.domain.approval import Approval
from waywarden.domain.ids import ApprovalId, RunId


def test_approval_state_literal_enforced() -> None:
    with pytest.raises(ValueError, match="state must be one of"):
        Approval(
            id=ApprovalId("approval-1"),
            run_id=RunId("run-1"),
            approval_kind="tool-call",
            requested_capability="send_email",
            summary="Request permission to send the release note",
            state="approved",  # type: ignore[arg-type]
            requested_at=datetime(2026, 4, 19, 14, 0, tzinfo=UTC),
            decided_at=None,
            decided_by=None,
            expires_at=datetime(2026, 4, 19, 15, 0, tzinfo=UTC),
        )


def test_decided_fields_coherent_with_state() -> None:
    with pytest.raises(
        ValueError,
        match="pending approvals must not have decided_at or decided_by",
    ):
        Approval(
            id=ApprovalId("approval-1"),
            run_id=RunId("run-1"),
            approval_kind="tool-call",
            requested_capability=None,
            summary="Wait for operator approval",
            state="pending",
            requested_at=datetime(2026, 4, 19, 14, 0, tzinfo=UTC),
            decided_at=datetime(2026, 4, 19, 14, 5, tzinfo=UTC),
            decided_by="operator",
            expires_at=datetime(2026, 4, 19, 15, 0, tzinfo=UTC),
        )

    with pytest.raises(
        ValueError,
        match="decided_at must be set once approval state is not pending",
    ):
        Approval(
            id=ApprovalId("approval-2"),
            run_id=RunId("run-2"),
            approval_kind="tool-call",
            requested_capability=None,
            summary="Wait for operator approval",
            state="granted",
            requested_at=datetime(2026, 4, 19, 14, 0, tzinfo=UTC),
            decided_at=None,
            decided_by="operator",
            expires_at=datetime(2026, 4, 19, 15, 0, tzinfo=UTC),
        )


def test_expires_at_must_be_timezone_aware_and_normalized_to_utc() -> None:
    with pytest.raises(ValueError, match="expires_at must be timezone-aware"):
        Approval(
            id=ApprovalId("approval-1"),
            run_id=RunId("run-1"),
            approval_kind="tool-call",
            requested_capability=None,
            summary="Wait for operator approval",
            state="pending",
            requested_at=datetime(2026, 4, 19, 14, 0, tzinfo=UTC),
            decided_at=None,
            decided_by=None,
            expires_at=datetime(2026, 4, 19, 15, 0),
        )

    approval = Approval(
        id=ApprovalId("approval-2"),
        run_id=RunId("run-2"),
        approval_kind="tool-call",
        requested_capability=None,
        summary="Wait for operator approval",
        state="pending",
        requested_at=datetime(2026, 4, 19, 14, 0, tzinfo=UTC),
        decided_at=None,
        decided_by=None,
        expires_at=datetime(2026, 4, 19, 11, 0, tzinfo=timezone(timedelta(hours=-4))),
    )

    assert approval.expires_at == datetime(2026, 4, 19, 15, 0, tzinfo=UTC)
