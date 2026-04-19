"""Provider-neutral message domain model."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Literal, cast, get_args

from waywarden.domain.ids import MessageId, SessionId

MessageRole = Literal["user", "assistant", "system", "tool"]
_VALID_ROLES: frozenset[str] = frozenset(get_args(MessageRole))


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


def _normalize_role(value: MessageRole | str) -> MessageRole:
    normalized = _require_non_empty_text(value, field_name="role")
    if normalized not in _VALID_ROLES:
        raise ValueError("role must be one of 'user', 'assistant', 'system', or 'tool'")
    return cast(MessageRole, normalized)


def _normalize_metadata(metadata: Mapping[str, str]) -> Mapping[str, str]:
    if not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping")

    normalized_metadata: dict[str, str] = {}

    for key, value in metadata.items():
        if not isinstance(key, str):
            raise TypeError("metadata keys must be strings")
        if not isinstance(value, str):
            raise TypeError(f"metadata[{key!r}] must be a string")
        normalized_metadata[key] = value

    return MappingProxyType(normalized_metadata)


@dataclass(frozen=True, slots=True)
class Message:
    """One immutable message in a provider-neutral session transcript."""

    id: MessageId
    session_id: SessionId
    role: MessageRole
    content: str
    created_at: datetime
    metadata: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "id",
            MessageId(_require_non_empty_text(self.id, field_name="id")),
        )
        object.__setattr__(
            self,
            "session_id",
            SessionId(_require_non_empty_text(self.session_id, field_name="session_id")),
        )
        object.__setattr__(self, "role", _normalize_role(self.role))
        if not isinstance(self.content, str):
            raise TypeError("content must be a string")
        object.__setattr__(
            self,
            "created_at",
            _require_aware_datetime(self.created_at, field_name="created_at"),
        )
        object.__setattr__(self, "metadata", _normalize_metadata(self.metadata))
