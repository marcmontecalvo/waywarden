"""Context builder — assembles PromptEnvelope from memory + knowledge.

The ContextBuilder reads recent memory entries and knowledge hits for a
session and assembles them into a typed PromptEnvelope.  Memory and
knowledge are kept in separate blocks (ADR-0003).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from logging import getLogger
from typing import TYPE_CHECKING

from waywarden.config.settings import AppConfig
from waywarden.domain.ids import SessionId
from waywarden.domain.providers.types.knowledge import KnowledgeHit
from waywarden.domain.providers.types.memory import MemoryEntry
from waywarden.domain.providers.types.model import PromptEnvelope

if TYPE_CHECKING:
    from waywarden.domain.providers import KnowledgeProvider, MemoryProvider
    from waywarden.domain.providers.types.memory import MemoryQuery

logger = getLogger(__name__)

DEFAULT_MAX_MEMORY = 10
DEFAULT_MAX_KNOWLEDGE = 5


@dataclass(frozen=True, slots=True)
class ContextBuilder:
    """Assembles a PromptEnvelope from memory + knowledge providers.

    Parameters
    ----------
    memory_provider:
        The memory provider to read session history from.
    knowledge_provider:
        The knowledge provider to search for relevant documents.
    config:
        Application configuration carrying truncation caps.
    """

    _memory: MemoryProvider = field(repr=False)
    _knowledge: KnowledgeProvider = field(repr=False)
    _memory_cap: int
    _knowledge_cap: int

    def __post_init__(self) -> None:
        """Validate that both providers are non-None and caps are valid."""
        if self._memory is None or self._knowledge is None:
            raise ValueError("memory_provider and knowledge_provider must not be None")
        if self._memory_cap < 0:
            raise ValueError("context_memory_char_cap must be >= 0")
        if self._knowledge_cap < 0:
            raise ValueError("context_knowledge_char_cap must be >= 0")

    @classmethod
    def from_config(
        cls,
        memory_provider: MemoryProvider,
        knowledge_provider: KnowledgeProvider,
        config: AppConfig,
    ) -> ContextBuilder:
        """Create a ContextBuilder using the application config values."""
        return cls(
            _memory=memory_provider,
            _knowledge=knowledge_provider,
            _memory_cap=config.context_memory_char_cap,
            _knowledge_cap=config.context_knowledge_char_cap,
        )

    async def build(
        self,
        session_id: SessionId,
        user_input: str,
        *,
        max_memory: int = DEFAULT_MAX_MEMORY,
        max_knowledge: int = DEFAULT_MAX_KNOWLEDGE,
    ) -> PromptEnvelope:
        """Assemble a PromptEnvelope for the given session and user input.

        Memory and knowledge are queried from their providers, truncated to
        the configured char caps, and placed into separate blocks inside the
        envelope.  No merging of the two sources occurs.
        """
        memory_entries = await self._fetch_memory(session_id, max_memory)
        knowledge_hits = await self._fetch_knowledge(session_id, user_input, max_knowledge)
        memory_block = self._truncate_memory(memory_entries)
        knowledge_block = self._truncate_knowledge(knowledge_hits)

        messages = [user_input]

        return PromptEnvelope(
            session_id=session_id,
            messages=messages,
            memory_block=memory_block,
            knowledge_block=knowledge_block,
        )

    async def _fetch_memory(
        self, session_id: SessionId, max_entries: int
    ) -> list[MemoryEntry]:
        from waywarden.domain.providers.types.memory import MemoryQuery

        query: MemoryQuery = MemoryQuery(
            session_id=session_id, query_text="", limit=max_entries
        )
        raw = await self._memory.read(session_id, query)
        # Enforce the limit at the builder level as a safety net
        return raw[:max_entries]

    async def _fetch_knowledge(
        self, session_id: SessionId, user_input: str, max_entries: int
    ) -> list[KnowledgeHit]:
        return await self._knowledge.search(user_input, limit=max_entries)

    def _truncate_memory(
        self, entries: list[MemoryEntry]
    ) -> tuple[MemoryEntry, ...]:
        if self._memory_cap <= 0:
            return ()
        result: list[MemoryEntry] = []
        cap = self._memory_cap
        for entry in entries:
            truncated = self._apply_cap(entry, cap)
            result.append(truncated)
        return tuple(result)

    def _truncate_knowledge(
        self, hits: list[KnowledgeHit]
    ) -> tuple[KnowledgeHit, ...]:
        if self._knowledge_cap <= 0:
            return ()
        result: list[KnowledgeHit] = []
        cap = self._knowledge_cap
        for hit in hits:
            truncated = self._apply_cap_knowledge(hit, cap)
            result.append(truncated)
        return tuple(result)

    def _apply_cap(self, entry: MemoryEntry, cap: int) -> MemoryEntry:
        """Truncate content to ``cap`` characters, returning a new frozen object."""
        if len(entry.content) > cap:
            return MemoryEntry(
                session_id=entry.session_id,
                content=entry.content[:cap],
                metadata=dict(entry.metadata),
                created_at=entry.created_at,
            )
        return entry

    def _apply_cap_knowledge(self, hit: KnowledgeHit, cap: int) -> KnowledgeHit:
        """Truncate knowledge-hit snippet to ``cap`` characters."""
        if len(hit.snippet) > cap:
            return KnowledgeHit(
                ref=hit.ref,
                title=hit.title,
                snippet=hit.snippet[:cap],
                score=hit.score,
            )
        return hit
