"""Provider-neutral session domain model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from waywarden.domain.ids import InstanceId, SessionId


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


@dataclass(frozen=True, slots=True)
class Session:
    """Stable conversation boundary for a single instance and profile."""

    id: SessionId
    instance_id: InstanceId
    profile: str
    created_at: datetime
    closed_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "id",
            SessionId(_require_non_empty_text(self.id, field_name="id")),
        )
        object.__setattr__(
            self,
            "instance_id",
            InstanceId(_require_non_empty_text(self.instance_id, field_name="instance_id")),
        )
        object.__setattr__(
            self,
            "profile",
            _require_non_empty_text(self.profile, field_name="profile"),
        )
        object.__setattr__(
            self,
            "created_at",
            _require_aware_datetime(self.created_at, field_name="created_at"),
        )
        if self.closed_at is not None:
            object.__setattr__(
                self,
                "closed_at",
                _require_aware_datetime(self.closed_at, field_name="closed_at"),
            )
