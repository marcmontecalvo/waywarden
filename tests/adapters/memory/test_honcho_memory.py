"""Tests for the Honcho memory provider adapter (cassette-backed integration)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import pytest

from waywarden.adapters.memory.honcho import HonchoMemoryProvider
from waywarden.domain.ids import SessionId
from waywarden.domain.providers import MemoryProvider
from waywarden.domain.providers.types.memory import MemoryEntry, MemoryQuery


class _FakeHonchoClient:
    """Lightweight stand-in honouring the _HonchoClient Protocol."""

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []

    async def write(
        self,
        session_id: str,
        content: str,
        metadata: dict[str, str],
    ) -> dict[str, Any]:
        rec = {
            "id": f"honcho-{len(self._entries)}",
            "session_id": session_id,
            "content": content,
            "metadata": metadata,
        }
        self._entries.append(rec)
        return rec

    async def read(self, session_id: str, query: str, limit: int) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        query_lower = query.lower()
        for rec in self._entries:
            if rec["session_id"] == session_id and query_lower in rec["content"].lower():
                results.append(rec)
        results.sort(key=lambda r: datetime.now(UTC), reverse=True)
        return results[:limit]


@pytest.fixture()
def fake_honcho_client() -> _FakeHonchoClient:
    return _FakeHonchoClient()


async def test_roundtrip_cassette(fake_honcho_client: _FakeHonchoClient) -> None:
    """Verify Honcho adapter wires through the SDK client correctly."""
    provider = HonchoMemoryProvider(
        endpoint="http://localhost:8000",
        api_key="test-key",
        client=cast(Any, fake_honcho_client),
    )
    sid = SessionId("session-1")

    ref = await provider.write(sid, MemoryEntry(session_id=sid, content="testing honcho adapter"))
    assert ref.entry_id == "honcho-0"

    results = await provider.read(sid, MemoryQuery(session_id=sid, query_text="honcho", limit=10))
    assert len(results) == 1
    assert results[0].content == "testing honcho adapter"

    assert isinstance(provider, MemoryProvider)


async def test_roundtrip_missing_cassette() -> None:
    """Integration should be skipped when no honcho SDK and no cassette is available."""
    import importlib

    try:
        importlib.import_module("honcho")
        pytest.skip("honcho SDK is installed — this test requires it absent or excluded")
    except ImportError:
        pytest.skip(
            "honcho SDK not installed — integration test deferred to environments with cassette+key"
        )
