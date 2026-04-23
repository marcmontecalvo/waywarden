"""Memory provider protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from waywarden.domain.ids import SessionId
from waywarden.domain.providers.types.memory import MemoryEntry, MemoryEntryRef, MemoryQuery


@runtime_checkable
class MemoryProvider(Protocol):
    """Protocol for memory providers.

    Memory and knowledge are kept distinct (ADR-0003): this Protocol
    does not inherit from any shared base.
    """

    async def write(self, session_id: SessionId, entry: MemoryEntry) -> MemoryEntryRef: ...

    async def read(
        self,
        session_id: SessionId,
        query: MemoryQuery,
    ) -> list[MemoryEntry]: ...
