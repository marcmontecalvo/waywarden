"""Tests for ContextBuilder — memory + knowledge -> PromptEnvelope."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from tests.services.fake_knowledge import FakeKnowledgeProvider
from waywarden.domain.ids import SessionId
from waywarden.domain.providers.types.knowledge import KnowledgeHit
from waywarden.domain.providers.types.memory import MemoryEntry
from waywarden.services.context_builder import ContextBuilder


def _make_memory_mock() -> AsyncMock:
    """Return an AsyncMock that satisfies the MemoryProvider protocol."""
    mem_mock = AsyncMock()
    return mem_mock


def _make_config_mock(
    memory_cap: int = 2000, knowledge_cap: int = 2000
) -> MagicMock:
    config = MagicMock()
    config.context_memory_char_cap = memory_cap
    config.context_knowledge_char_cap = knowledge_cap
    return config


class TestContextBuilderBasic:
    """Basic ContextBuilder functionality."""

    async def test_build_returns_prompt_envelope(self) -> None:
        sid = SessionId("test-session")
        mem_mock = AsyncMock()
        config = _make_config_mock()
        kb = FakeKnowledgeProvider()

        builder = ContextBuilder.from_config(mem_mock, kb, config)
        envelope = await builder.build(sid, "hello world")

        assert envelope.session_id == sid
        assert envelope.messages == ["hello world"]

    async def test_memory_and_knowledge_separate_blocks(self) -> None:
        """P3-6 AC1 build() returns a PromptEnvelope with both lists populated."""
        sid = SessionId("test-session")
        mem_mock = AsyncMock()

        mem_entry = MemoryEntry(session_id=sid, content="recent memory data")
        mem_mock.read.return_value = [mem_entry]

        kb = FakeKnowledgeProvider(
            hits=[
                KnowledgeHit(
                    ref="adr0003",
                    title="Memory vs Knowledge",
                    snippet="Memory and knowledge are kept distinct (ADR-0003)",
                    score=1.5,
                ),
            ]
        )
        config = _make_config_mock()

        builder = ContextBuilder.from_config(mem_mock, kb, config)
        envelope = await builder.build(sid, "memory and knowledge query")

        # Both blocks must be present
        assert isinstance(envelope.memory_block, tuple)
        assert isinstance(envelope.knowledge_block, tuple)
        assert len(envelope.memory_block) == 1
        assert len(envelope.knowledge_block) == 1

        # Memory block contains the memory entry
        assert envelope.memory_block[0].content == "recent memory data"

        # Knowledge block contains the knowledge hit
        assert envelope.knowledge_block[0].ref == "adr0003"

    async def test_no_merged_block(self) -> None:
        """P3-6 AC2 No runtime path merges memory + knowledge into one block."""
        sid = SessionId("test-session")
        mem_mock = AsyncMock()
        mem_entry = MemoryEntry(session_id=sid, content="mem data")
        mem_mock.read.return_value = [mem_entry]

        kb = FakeKnowledgeProvider(
            hits=[
                KnowledgeHit(
                    ref="doc1",
                    title="Doc 1",
                    snippet="knowledge about something",
                    score=1.0,
                ),
            ]
        )
        config = _make_config_mock()

        builder = ContextBuilder.from_config(mem_mock, kb, config)
        envelope = await builder.build(sid, "doc doc1 knowledge")

        # Memory and knowledge must remain in separate fields
        assert envelope.memory_block == (
            MemoryEntry(
                session_id=sid,
                content="mem data",
                metadata={},
                created_at=envelope.memory_block[0].created_at,
            ),
        )
        assert envelope.knowledge_block == (
            KnowledgeHit(
                ref="doc1",
                title="Doc 1",
                snippet="knowledge about something",
                score=1.0,
            ),
        )
        # The fields are distinct — no single list contains both types.
        # Compare types separately since MemoryEntry has a dict metadata.
        mem_types = {type(e).__name__ for e in envelope.memory_block}
        kb_types = {type(k).__name__ for k in envelope.knowledge_block}
        assert "MemoryEntry" in mem_types

    async def test_bounded_by_max_params(self) -> None:
        """P3-6 AC3 max_memory and max_knowledge limit the blocks."""
        sid = SessionId("test-session")
        mem_mock = AsyncMock()
        mem_entries = [
            MemoryEntry(session_id=sid, content=f"entry {i}")
            for i in range(20)
        ]
        mem_mock.read.return_value = mem_entries

        kb = FakeKnowledgeProvider(
            hits=[
                KnowledgeHit(ref=f"doc{i}", title=f"Doc {i}", snippet=f"content {i}", score=1.0)
                for i in range(20)
            ]
        )
        config = _make_config_mock()

        builder = ContextBuilder.from_config(mem_mock, kb, config)

        # Explicit bounds
        envelope = await builder.build(
            sid, "doc doci content", max_memory=3, max_knowledge=2
        )
        assert len(envelope.memory_block) == 3
        assert len(envelope.knowledge_block) == 2

        # Default bounds
        envelope2 = await builder.build(sid, "doc d1 content")
        assert len(envelope2.memory_block) == min(len(mem_entries), 10)
        assert len(envelope2.knowledge_block) == min(len(kb._hits), 5)

    async def test_bounded_by_max_params_when_fewer_than_limit(self) -> None:
        """When available entries < max params, return what is available."""
        sid = SessionId("test-session")
        mem_mock = AsyncMock()
        mem_entries = [MemoryEntry(session_id=sid, content=f"mem {i}") for i in range(3)]
        mem_mock.read.return_value = mem_entries

        kb = FakeKnowledgeProvider(
            hits=[
                KnowledgeHit(ref=f"d{i}", title=f"D{i}", snippet="d0 d1 s0 s1", score=1.0)
                for i in range(2)
            ]
        )
        config = _make_config_mock()

        builder = ContextBuilder.from_config(mem_mock, kb, config)

        envelope = await builder.build(sid, "mem d1 s1", max_memory=10, max_knowledge=10)
        # Fallback to actual available count
        assert len(envelope.memory_block) == 3
        assert len(envelope.knowledge_block) == 2

    async def test_truncation_caps_applied(self) -> None:
        """P3-6 AC3 Truncation caps are honored; tested with synthetic long entries."""
        sid = SessionId("test-session")
        mem_mock = AsyncMock()
        long_content = "x" * 5000
        mem_entry = MemoryEntry(session_id=sid, content=long_content)
        mem_mock.read.return_value = [mem_entry]

        kb = FakeKnowledgeProvider(
            hits=[
                KnowledgeHit(
                    ref="long-doc",
                    title="Long document",
                    snippet="y" * 5000,
                    score=1.0,
                ),
            ]
        )
        config = _make_config_mock(memory_cap=1000, knowledge_cap=1500)

        builder = ContextBuilder.from_config(mem_mock, kb, config)
        envelope = await builder.build(sid, "long document")

        # Memory content truncated to 1000 chars
        assert len(envelope.memory_block[0].content) == 1000
        assert envelope.memory_block[0].content == "x" * 1000

        # Knowledge snippet truncated to 1500 chars
        assert len(envelope.knowledge_block[0].snippet) == 1500
        assert envelope.knowledge_block[0].snippet == "y" * 1500

    async def test_no_truncation_when_within_cap(self) -> None:
        """Short entries are not modified when under cap."""
        sid = SessionId("test-session")
        mem_mock = AsyncMock()
        mem_entry = MemoryEntry(session_id=sid, content="short")
        mem_mock.read.return_value = [mem_entry]

        kb = FakeKnowledgeProvider(
            hits=[
                KnowledgeHit(ref="d1", title="D1", snippet="short snippet", score=1.0),
            ]
        )
        config = _make_config_mock(memory_cap=2000, knowledge_cap=2000)

        builder = ContextBuilder.from_config(mem_mock, kb, config)
        envelope = await builder.build(sid, "d1 short snippet", max_memory=10, max_knowledge=10)

        assert envelope.memory_block[0].content == "short"
        assert envelope.knowledge_block[0].snippet == "short snippet"

    async def test_zero_cap_yields_empty_blocks(self) -> None:
        """Zero cap means no content is included."""
        sid = SessionId("test-session")
        mem_mock = AsyncMock()
        mem_mock.read.return_value = [
            MemoryEntry(session_id=sid, content="content")
        ]

        kb = FakeKnowledgeProvider(
            hits=[
                KnowledgeHit(ref="d1", title="D1", snippet="snippet", score=1.0),
            ]
        )
        config = _make_config_mock(memory_cap=0, knowledge_cap=0)

        builder = ContextBuilder.from_config(mem_mock, kb, config)
        envelope = await builder.build(sid, "zero cap query")

        assert len(envelope.memory_block) == 0
        assert len(envelope.knowledge_block) == 0

    async def test_metadata_preserved_after_truncation(self) -> None:
        """Truncation must not lose metadata."""
        sid = SessionId("test-session")
        mem_mock = AsyncMock()
        long_content = "a" * 5000
        mem_entry = MemoryEntry(
            session_id=sid,
            content=long_content,
            metadata={"key": "value", "source": "test"},
        )
        mem_mock.read.return_value = [mem_entry]

        kb = FakeKnowledgeProvider()
        config = _make_config_mock(memory_cap=100, knowledge_cap=2000)

        builder = ContextBuilder.from_config(mem_mock, kb, config)
        envelope = await builder.build(sid, "metadata test")

        assert envelope.memory_block[0].metadata["key"] == "value"
        assert envelope.memory_block[0].metadata["source"] == "test"

    async def test_empty_memory_and_knowledge(self) -> None:
        """When providers return nothing, envelope has empty blocks."""
        sid = SessionId("test-session")
        mem_mock = AsyncMock()
        mem_mock.read.return_value = []

        kb = FakeKnowledgeProvider()
        config = _make_config_mock()

        builder = ContextBuilder.from_config(mem_mock, kb, config)
        envelope = await builder.build(sid, "empty query")

        assert len(envelope.memory_block) == 0
        assert len(envelope.knowledge_block) == 0
