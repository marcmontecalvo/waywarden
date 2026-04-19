"""Provider-neutral approval domain model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, cast, get_args

from waywarden.domain.ids import ApprovalId, RunId

ApprovalState = Literal["pending", "granted", "denied", "timeout"]
_VALID_STATES: frozenset[str] = frozenset(get_args(ApprovalState))


def _require_non_empty_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    trimmed = value.strip()
    if not trimmed:
        raise ValueError(f"{field_name} must not be blank")
    return trimmed


def _require_aware_datetime(value: datetime, *, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


def _normalize_utc_datetime(value: datetime, *, field_name: str) -> datetime:
    normalized = _require_aware_datetime(value, field_name=field_name)
    return normalized.astimezone(UTC)


def _normalize_state(value: ApprovalState | str) -> ApprovalState:
    normalized = _require_non_empty_text(value, field_name="state")
    if normalized not in _VALID_STATES:
        raise ValueError("state must be one of 'pending', 'granted', 'denied', or 'timeout'")
    return cast(ApprovalState, normalized)


@dataclass(frozen=True, slots=True)
class Approval:
    """Immutable persisted approval decision artifact referenced by RT-002 events."""

    id: ApprovalId
    run_id: RunId
    approval_kind: str
    requested_capability: str | None
    summary: str
    state: ApprovalState
    requested_at: datetime
    decided_at: datetime | None
    decided_by: str | None
    expires_at: datetime | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "id",
            ApprovalId(_require_non_empty_text(self.id, field_name="id")),
        )
        object.__setattr__(
            self,
            "run_id",
            RunId(_require_non_empty_text(self.run_id, field_name="run_id")),
        )
        object.__setattr__(
            self,
            "approval_kind",
            _require_non_empty_text(self.approval_kind, field_name="approval_kind"),
        )
        if self.requested_capability is not None:
            object.__setattr__(
                self,
                "requested_capability",
                _require_non_empty_text(
                    self.requested_capability,
                    field_name="requested_capability",
                ),
            )
        object.__setattr__(
            self,
            "summary",
            _require_non_empty_text(self.summary, field_name="summary"),
        )
        object.__setattr__(self, "state", _normalize_state(self.state))

        requested_at = _require_aware_datetime(self.requested_at, field_name="requested_at")
        object.__setattr__(self, "requested_at", requested_at)

        decided_at = self.decided_at
        if decided_at is not None:
            decided_at = _require_aware_datetime(decided_at, field_name="decided_at")
            if decided_at < requested_at:
                raise ValueError("decided_at must not be before requested_at")
            object.__setattr__(self, "decided_at", decided_at)

        if self.decided_by is not None:
            object.__setattr__(
                self,
                "decided_by",
                _require_non_empty_text(self.decided_by, field_name="decided_by"),
            )

        if self.expires_at is not None:
            object.__setattr__(
                self,
                "expires_at",
                _normalize_utc_datetime(self.expires_at, field_name="expires_at"),
            )

        if self.state == "pending":
            if self.decided_at is not None or self.decided_by is not None:
                raise ValueError("pending approvals must not have decided_at or decided_by")
            return

        if self.decided_at is None:
            raise ValueError("decided_at must be set once approval state is not pending")
