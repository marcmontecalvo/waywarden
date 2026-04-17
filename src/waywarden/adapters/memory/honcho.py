from waywarden.adapters.memory.base import MemoryProvider
from waywarden.domain.models.memory_ref import MemoryItem


class HonchoMemoryProvider(MemoryProvider):
    async def fetch_context(
        self, *, subject_id: str, query: str, limit: int = 20
    ) -> list[MemoryItem]:
        return []

    async def write_event(
        self, *, subject_id: str, event: dict[str, object]
    ) -> None:
        return None

    async def consolidate(self, *, subject_id: str) -> dict[str, object]:
        return {"status": "noop"}
