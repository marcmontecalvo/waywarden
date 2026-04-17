from typing import Protocol

from waywarden.domain.models.memory_ref import MemoryItem


class MemoryProvider(Protocol):
    async def fetch_context(
        self, *, subject_id: str, query: str, limit: int = 20
    ) -> list[MemoryItem]: ...

    async def write_event(self, *, subject_id: str, event: dict[str, object]) -> None: ...

    async def consolidate(self, *, subject_id: str) -> dict[str, object]: ...
