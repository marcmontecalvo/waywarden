from typing import Protocol

from waywarden.domain.models.knowledge_ref import KnowledgeHit


class KnowledgeProvider(Protocol):
    async def search(
        self, *, query: str, scope: list[str] | None = None, limit: int = 10
    ) -> list[KnowledgeHit]: ...

    async def ingest(self, *, source_uri: str, metadata: dict[str, str]) -> dict[str, object]: ...

    async def refresh(self, *, scope: list[str] | None = None) -> dict[str, object]: ...
