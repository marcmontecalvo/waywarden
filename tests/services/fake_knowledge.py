"""Deterministic in-repo fake knowledge provider for tests."""

from __future__ import annotations

from waywarden.domain.providers.types.knowledge import (
    KnowledgeDocument,
    KnowledgeHit,
)


class FakeKnowledgeProvider:
    """In-memory knowledge provider for unit testing.

    Returns all hits matching the query by simple substring overlap on tokens.
    If empty query, returns everything sorted.
    """

    def __init__(self, hits: list[KnowledgeHit] | None = None) -> None:
        self._hits: list[KnowledgeHit] = hits or []

    def populate(self, hits: list[KnowledgeHit]) -> None:
        self._hits = list(hits)

    async def search(
        self,
        query: str,
        *,
        limit: int = 10,
    ) -> list[KnowledgeHit]:
        query_lower = query.lower()
        if not query_lower:
            matched = list(self._hits)
        else:
            query_tokens = set(query_lower.split())
            matched = []
            for hit in self._hits:
                hit_text = (hit.title + " " + hit.snippet).lower()
                if any(t in hit_text for t in query_tokens):
                    matched.append(hit)
        matched.sort(key=lambda h: (-h.score, h.ref))
        return matched[:limit]

    async def fetch(self, ref: str) -> KnowledgeDocument:
        for hit in self._hits:
            if hit.ref == ref:
                return KnowledgeDocument(
                    ref=hit.ref,
                    title=hit.title,
                    content=hit.snippet,
                )
        from waywarden.adapters.knowledge.filesystem import KnowledgeNotFound

        raise KnowledgeNotFound(f"knowledge document not found: {ref}")
