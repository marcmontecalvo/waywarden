from ea.adapters.memory.base import MemoryProvider
from ea.domain.models.memory_ref import MemoryItem


class FakeMemoryProvider(MemoryProvider):
    async def fetch_context(self, *, subject_id: str, query: str, limit: int = 20) -> list[MemoryItem]:
        return [MemoryItem(id="fake-1", text="User prefers concise answers.")]

    async def write_event(self, *, subject_id: str, event: dict[str, object]) -> None:
        return None

    async def consolidate(self, *, subject_id: str) -> dict[str, object]:
        return {"status": "ok"}
