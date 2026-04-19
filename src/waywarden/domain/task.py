"""Provider-neutral task domain model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, cast, get_args

from waywarden.domain.ids import SessionId, TaskId

TaskState = Literal[
    "draft",
    "planning",
    "executing",
    "waiting_approval",
    "completed",
    "failed",
    "cancelled",
]
_VALID_STATES: frozenset[str] = frozenset(get_args(TaskState))


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


def _normalize_state(value: TaskState | str) -> TaskState:
    normalized = _require_non_empty_text(value, field_name="state")
    if normalized not in _VALID_STATES:
        raise ValueError(
            "state must be one of 'draft', 'planning', 'executing', 'waiting_approval', "
            "'completed', 'failed', or 'cancelled'"
        )
    return cast(TaskState, normalized)


@dataclass(frozen=True, slots=True)
class Task:
    """Immutable task record aligned to the RT-002 run lifecycle."""

    id: TaskId
    session_id: SessionId
    title: str
    objective: str
    state: TaskState
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "id",
            TaskId(_require_non_empty_text(self.id, field_name="id")),
        )
        object.__setattr__(
            self,
            "session_id",
            SessionId(_require_non_empty_text(self.session_id, field_name="session_id")),
        )
        object.__setattr__(
            self,
            "title",
            _require_non_empty_text(self.title, field_name="title"),
        )
        object.__setattr__(
            self,
            "objective",
            _require_non_empty_text(self.objective, field_name="objective"),
        )
        object.__setattr__(self, "state", _normalize_state(self.state))

        created_at = _require_aware_datetime(self.created_at, field_name="created_at")
        updated_at = _require_aware_datetime(self.updated_at, field_name="updated_at")
        if updated_at < created_at:
            raise ValueError("updated_at must not be before created_at")

        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "updated_at", updated_at)
