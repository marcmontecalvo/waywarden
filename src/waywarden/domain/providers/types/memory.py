"""Value types for the memory provider protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from waywarden.domain.ids import SessionId


@dataclass(frozen=True, slots=True)
class MemoryEntryRef:
    """Opaque reference to a stored memory entry."""

    entry_id: str
    session_id: SessionId


@dataclass(frozen=True, slots=True)
class MemoryQuery:
    """Parameters for a memory read operation."""

    session_id: SessionId
    query_text: str
    limit: int = 10

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id must not be empty")
        if not isinstance(self.query_text, str):
            raise TypeError("query_text must be a string")
        if self.limit < 1:
            raise ValueError("limit must be >= 1")


@dataclass(frozen=True, slots=True)
class MemoryEntry:
    """A single memory entry stored by the memory provider."""

    session_id: SessionId
    content: str
    metadata: dict[str, str] = field(default_factory=dict)
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id must not be empty")
        if not isinstance(self.content, str):
            raise TypeError("content must be a string")
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dict")
        for k, v in self.metadata.items():
            if not isinstance(k, str) or not isinstance(v, str):
                raise TypeError("metadata keys and values must be strings")
        if self.created_at is None:
            object.__setattr__(self, "created_at", datetime.now(UTC))
        elif not isinstance(self.created_at, datetime):
            raise TypeError("created_at must be a datetime")
        else:
            if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
                raise ValueError("created_at must be timezone-aware")
            object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))
