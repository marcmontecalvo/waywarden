"""Honcho memory provider adapter.

Gated behind the ``honcho`` optional dependency.
"""

from __future__ import annotations

from datetime import UTC, datetime
from importlib import import_module
from typing import Protocol

from waywarden.domain.ids import SessionId
from waywarden.domain.providers.types.memory import MemoryEntry, MemoryEntryRef, MemoryQuery


class _HonchoClient(Protocol):
    """Minimal honcho SDK protocol to avoid hard dependency import."""

    async def write(
        self,
        session_id: str,
        content: str,
        metadata: dict[str, str],
    ) -> object: ...

    async def read(
        self,
        session_id: str,
        query: str,
        limit: int,
    ) -> list[object]: ...


class HonchoMemoryProvider:
    """MemoryProvider backed by the Honcho SDK."""

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        client: _HonchoClient | None = None,
    ) -> None:
        if not endpoint.strip():
            raise ValueError("endpoint must not be empty")
        if not api_key.strip():
            raise ValueError("api_key must not be empty")

        self._endpoint = endpoint
        self._client = client or self._build_client(api_key)

    async def write(
        self,
        session_id: SessionId,
        entry: MemoryEntry,
    ) -> MemoryEntryRef:
        result = await self._client.write(
            session_id=session_id,
            content=entry.content,
            metadata=entry.metadata,
        )
        entry_id = self._extract_id(result)
        return MemoryEntryRef(entry_id=entry_id, session_id=session_id)

    async def read(
        self,
        session_id: SessionId,
        query: MemoryQuery,
    ) -> list[MemoryEntry]:
        records = await self._client.read(
            session_id=session_id,
            query=query.query_text,
            limit=query.limit,
        )

        entries: list[MemoryEntry] = []
        for rec in records:
            raw_sid = self._rec_str(rec, "session_id")
            entry_sid = SessionId(raw_sid) if raw_sid else session_id

            raw_content = self._rec_str(rec, "content")
            raw_meta = self._rec_dict(rec, "metadata")
            raw_created = self._rec_created(rec, "created_at")

            entry = MemoryEntry(
                session_id=entry_sid,
                content=raw_content or "",
                metadata=raw_meta or {},
                created_at=raw_created or datetime.now(UTC),
            )
            entries.append(entry)

        return entries

    def _build_client(self, api_key: str) -> _HonchoClient:
        module = import_module("honcho")
        client_cls = module.__dict__["HonchoClient"]
        return client_cls(api_key=api_key, endpoint=self._endpoint)  # type: ignore[no-any-return]

    def _extract_id(self, result: object) -> str:
        if isinstance(result, dict):
            return str(result.get("id", result.get("entry_id", "unknown")))
        return str(getattr(result, "id", getattr(result, "entry_id", "unknown")))

    @staticmethod
    def _rec_str(rec: object, key: str) -> str | None:
        if isinstance(rec, dict):
            return rec.get(key)
        return getattr(rec, key, None)

    @staticmethod
    def _rec_dict(rec: object, key: str) -> dict[str, str] | None:
        if isinstance(rec, dict):
            val = rec.get(key)
            if isinstance(val, dict):
                return val
            return None
        val = getattr(rec, key, None)
        if isinstance(val, dict):
            return val
        return None

    @staticmethod
    def _rec_created(rec: object, key: str) -> datetime | None:
        val = rec.get(key) if isinstance(rec, dict) else getattr(rec, key, None)
        if isinstance(val, datetime):
            return val
        if isinstance(val, str):
            return datetime.fromisoformat(val)
        return None
