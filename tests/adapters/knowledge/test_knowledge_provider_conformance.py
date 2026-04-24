"""Protocol conformance tests for knowledge providers."""

from __future__ import annotations

from pathlib import Path

import pytest

from waywarden.domain.providers.knowledge import KnowledgeProvider
from waywarden.domain.providers.types.knowledge import KnowledgeDocument, KnowledgeHit


def test_filesystem_provider_implements_knowledge_provider() -> None:
    """FilesystemKnowledgeProvider must pass isinstance(knowledge_provider)."""
    from waywarden.adapters.knowledge.filesystem import FilesystemKnowledgeProvider

    # Use a real directory — assets/knowledge/ exists on disk
    root = Path(__file__).parent.parent.parent.parent.parent / "assets" / "knowledge"
    if not root.is_dir():
        pytest.skip(f"assets/knowledge/ not found at {root}")

    provider = FilesystemKnowledgeProvider(root=root)
    assert isinstance(provider, KnowledgeProvider), (
        "FilesystemKnowledgeProvider does not implement KnowledgeProvider protocol"
    )


def test_filesystem_provider_search_and_fetch_awaitable() -> None:
    """FilesystemKnowledgeProvider's search and fetch must be awaitable."""

    async def check() -> None:
        root = Path(__file__).parent.parent.parent.parent.parent / "assets" / "knowledge"
        if not root.is_dir():
            pytest.skip(f"assets/knowledge/ not found at {root}")

        provider = FilesystemKnowledgeProvider(root=root)

        # search returns list[KnowledgeHit]
        results = await provider.search("memory")
        for r in results:
            assert isinstance(r, KnowledgeHit)

        # fetch returns KnowledgeDocument
        if results:
            doc = await provider.fetch(results[0].ref)
            assert isinstance(doc, KnowledgeDocument)

    import asyncio

    asyncio.run(check())


async def test_filesystem_provider_handles_empty_directory(tmp_path: Path) -> None:
    """FilesystemKnowledgeProvider.search on an empty directory returns empty list."""
    from waywarden.adapters.knowledge.filesystem import FilesystemKnowledgeProvider

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    provider = FilesystemKnowledgeProvider(root=empty_dir)
    results = await provider.search("anything")
    assert results == []
    assert isinstance(results, list)


class _MockLlmWikiClient:
    """Minimal mock matching _LlmWikiClient Protocol."""

    async def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> LlmWikiResponse:
        # Return 404 for everything — provider should handle this gracefully
        return LlmWikiResponse(status_code=404)


class LlmWikiResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code

    async def text(self) -> str:
        return "[]"


async def test_llm_wiki_provider_implements_knowledge_provider() -> None:
    """LLMWikiKnowledgeProvider must pass isinstance(knowledge_provider) and handle 404."""
    from waywarden.adapters.knowledge.llm_wiki import LLMWikiKnowledgeProvider

    client = _MockLlmWikiClient()
    provider = LLMWikiKnowledgeProvider(
        endpoint="http://localhost:9999",
        client=client,
    )
    assert isinstance(provider, KnowledgeProvider), (
        "LLMWikiKnowledgeProvider does not implement KnowledgeProvider protocol"
    )

    # Should return empty list on 404 — not crash
    results = await provider.search("anything")
    assert results == []
