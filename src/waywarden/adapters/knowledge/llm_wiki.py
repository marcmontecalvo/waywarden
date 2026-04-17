from waywarden.adapters.knowledge.base import KnowledgeProvider
from waywarden.domain.models.knowledge_ref import KnowledgeHit


class LLMWikiKnowledgeProvider(KnowledgeProvider):
    async def search(
        self, *, query: str, scope: list[str] | None = None, limit: int = 10
    ) -> list[KnowledgeHit]:
        return []

    async def ingest(
        self, *, source_uri: str, metadata: dict[str, str]
    ) -> dict[str, object]:
        return {"status": "queued", "source_uri": source_uri, "metadata": metadata}

    async def refresh(self, *, scope: list[str] | None = None) -> dict[str, object]:
        return {"status": "queued"}
