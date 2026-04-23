"""Deterministic in-repo fake memory provider for tests and local development."""

from __future__ import annotations

from datetime import UTC, datetime

from waywarden.domain.ids import SessionId
from waywarden.domain.providers.types.memory import MemoryEntry, MemoryEntryRef, MemoryQuery


class FakeMemoryProvider:
    """In-memory dict keyed by session_id with deterministic ordering by created_at."""

    def __init__(self) -> None:
        # session_id -> list of (created_at, entry_id, MemoryEntry)
        self._store: dict[SessionId, list[tuple[datetime, str, MemoryEntry]]] = {}

    async def write(self, session_id: SessionId, entry: MemoryEntry) -> MemoryEntryRef:
        if entry.created_at is None:
            object.__setattr__(entry, "created_at", datetime.now(UTC))

        entry_id = f"{session_id[:4]}-{len(self._store.get(session_id, []))}"
        stored = MemoryEntry(
            session_id=entry.session_id,
            content=entry.content,
            metadata=dict(entry.metadata),
            created_at=entry.created_at,
        )

        self._store.setdefault(
            session_id, []
        ).append((stored.created_at or datetime.now(UTC), entry_id, stored))

        return MemoryEntryRef(entry_id=entry_id, session_id=session_id)

    async def read(
        self,
        session_id: SessionId,
        query: MemoryQuery,
    ) -> list[MemoryEntry]:
        records = self._store.get(session_id, [])

        # Filter by query text (case-insensitive substring match)
        filtered: list[tuple[datetime, str, MemoryEntry]] = []
        query_lower = query.query_text.lower()
        for created_at, _entry_id, entry in records:
            if query_lower in entry.content.lower():
                filtered.append((created_at, _entry_id, entry))

        # Sort by created_at (reverse = newest first), then limit
        filtered.sort(key=lambda r: r[0], reverse=True)

        entries: list[MemoryEntry] = []
        for _dt, _eid, entry in filtered[: query.limit]:
            entries.append(entry)

        return entries
