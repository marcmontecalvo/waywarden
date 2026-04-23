"""Tests for the deterministic in-repo fake memory provider."""

from __future__ import annotations

from waywarden.adapters.memory.fake import FakeMemoryProvider
from waywarden.domain.ids import SessionId
from waywarden.domain.providers import MemoryProvider
from waywarden.domain.providers.types.memory import MemoryEntry, MemoryQuery


async def test_write_read_roundtrip() -> None:
    provider = FakeMemoryProvider()
    sid = SessionId("test-session-1")

    # Write two entries
    ref1 = await provider.write(sid, MemoryEntry(session_id=sid, content="hello world"))
    ref2 = await provider.write(sid, MemoryEntry(session_id=sid, content="goodbye world"))

    assert ref1.entry_id.startswith("test")
    assert ref2.entry_id.startswith("test")

    # Read back with query matching all
    results = await provider.read(sid, MemoryQuery(session_id=sid, query_text="world", limit=10))
    assert len(results) == 2

    # Results are newest first by created_at
    assert results[0].content == "goodbye world"
    assert results[1].content == "hello world"

    # Read back with partial match
    results_hello = await provider.read(sid, MemoryQuery(session_id=sid, query_text="hello", limit=10))
    assert len(results_hello) == 1
    assert results_hello[0].content == "hello world"

    # Read with limit
    results_limited = await provider.read(sid, MemoryQuery(session_id=sid, query_text="world", limit=1))
    assert len(results_limited) == 1
    assert results_limited[0].content == "goodbye world"

    # Different session should be isolated
    sid2 = SessionId("test-session-2")
    results_sid2 = await provider.read(sid2, MemoryQuery(session_id=sid2, query_text="world", limit=10))
    assert len(results_sid2) == 0

    # Verify isinstance check against protocol
    assert isinstance(provider, MemoryProvider)
