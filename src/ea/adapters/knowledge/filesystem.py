from ea.adapters.knowledge.base import KnowledgeProvider
from ea.domain.models.knowledge_ref import KnowledgeHit


class FilesystemKnowledgeProvider(KnowledgeProvider):
    async def search(self, *, query: str, scope: list[str] | None = None, limit: int = 10) -> list[KnowledgeHit]:
        return []

    async def ingest(self, *, source_uri: str, metadata: dict[str, str]) -> dict[str, object]:
        return {"status": "stored-locally", "source_uri": source_uri}

    async def refresh(self, *, scope: list[str] | None = None) -> dict[str, object]:
        return {"status": "noop"}
