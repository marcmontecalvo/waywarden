"""Adversarial red-team tests for P3-4 memory adapters."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from waywarden.adapters.memory.honcho import HonchoMemoryProvider
from waywarden.domain.ids import SessionId
from waywarden.domain.providers.types.memory import MemoryEntry, MemoryQuery


class _HonchoReturningStrings:
    """Honcho client that mimics real honcho SDK string dates.

    Real honcho serializes dates as ISO-8601 strings, not datetime objects.
    The adapter should handle this by parsing ISO-8601 strings into datetime
    objects; previously _rec_created only looked for datetime instances and
    silently fell back to datetime.now(UTC).
    """

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []

    async def write(
        self,
        session_id: str,
        content: str,
        metadata: dict[str, str],
    ) -> dict[str, Any]:
        rec = {
            "id": f"rec-{len(self._entries)}",
            "session_id": session_id,
            "content": content,
            "metadata": metadata,
            "created_at": "2020-01-01T12:00:00+00:00",
        }
        self._entries.append(rec)
        return rec

    async def read(
        self,
        session_id: str,
        query: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        query_lower = query.lower()
        for rec in self._entries:
            if rec["session_id"] == session_id and query_lower in rec["content"].lower():
                results.append(rec)
        results.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return results[:limit]


async def test_honcho_adapter_handles_iso_string_created_at() -> None:
    """When honcho returns created_at as an ISO string, the adapter must
    parse it -- never fall back to datetime.now(UTC) silently.

    Fallback to now() masks the real business timestamp and makes
    chronological ordering useless.
    """
    client = _HonchoReturningStrings()
    provider = HonchoMemoryProvider(
        endpoint="http://localhost",
        api_key="test-key",
        client=cast(Any, client),
    )
    sid = SessionId("s1")

    await provider.write(sid, MemoryEntry(session_id=sid, content="test entry"))

    results = await provider.read(sid, MemoryQuery(session_id=sid, query_text="test", limit=10))
    assert len(results) == 1
    entry = results[0]

    assert entry.created_at is not None, (
        "HonchoMemoryProvider returned None created_at when the honcho adapter "
        "responded with a valid ISO-8601 string -- the adapter must parse ISO "
        "string dates, not silently fall back to datetime.now()."
    )

    # The created_at should be the honcho-returned date (2020-01-01),
    # not close to now. A six-year-old date is safely outside any threshold.
    now = datetime.now(UTC)
    assert abs((entry.created_at - now).total_seconds()) > 365 * 86400, (
        f"HonchoMemoryProvider returned created_at={entry.created_at} which is "
        f"within seconds of now={now}; this means the ISO string "
        "'2020-01-01T12:00:00+00:00' was silently discarded in favor of "
        "datetime.now() -- a data integrity bug."
    )
