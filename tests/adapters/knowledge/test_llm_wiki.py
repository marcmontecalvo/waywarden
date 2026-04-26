"""Cassette-backed integration tests for the LLM-Wiki knowledge adapter."""

from __future__ import annotations

import json
from typing import Any

import pytest

from waywarden.domain.providers.types.knowledge import (
    KnowledgeDocument,
    KnowledgeHit,
)


class CassetteWikiResponse:
    def __init__(self, payload: dict[str, Any], status: int = 200) -> None:
        self.status_code = status
        self._payload = payload

    async def text(self) -> str:
        return json.dumps(self._payload)


class CassetteWikiClient:
    def __init__(
        self,
        search_payload: dict[str, Any],
        fetch_payload: dict[str, Any] | None = None,
        fetch_status: int = 200,
    ) -> None:
        self._search_payload = search_payload
        self._fetch_payload = fetch_payload
        self._fetch_status = fetch_status
        self.calls: list[dict[str, Any]] = []

    async def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> CassetteWikiResponse:
        self.calls.append({"url": url, "headers": headers or {}})
        if "/wiki/search" in url:
            return CassetteWikiResponse(self._search_payload)
        if "/wiki/fetch" in url:
            if self._fetch_payload is None:
                return CassetteWikiResponse({}, status=self._fetch_status)
            return CassetteWikiResponse(self._fetch_payload, self._fetch_status)
        return CassetteWikiResponse({}, status=404)


async def test_roundtrip_cassette() -> None:
    """LLMWikiKnowledgeProvider passes a cassette-backed integration test."""
    from waywarden.adapters.knowledge.llm_wiki import LLMWikiKnowledgeProvider

    search_payload = [
        {
            "ref": "docs/concepts.md",
            "title": "Core Concepts",
            "snippet": "Knowledge providers power the LLM-Wiki service...",
        },
        {
            "ref": "api/reference.md",
            "title": "API Reference",
            "snippet": "The search endpoint returns matching documents...",
        },
    ]
    fetch_payload = {
        "ref": "docs/concepts.md",
        "title": "Core Concepts",
        "content": (
            "Knowledge providers power the LLM-Wiki service. They remain distinct from memory."
        ),
    }

    client = CassetteWikiClient(search_payload, fetch_payload)
    provider = LLMWikiKnowledgeProvider(
        endpoint="http://localhost:9999",
        api_key="test-key",
        client=client,
    )

    # Search
    results = await provider.search("knowledge")
    assert len(results) == 2
    assert isinstance(results[0], KnowledgeHit)
    assert results[0].ref == "docs/concepts.md"
    assert results[0].score == 1.0
    assert results[0].snippet == search_payload[0]["snippet"]
    assert results[1].ref == "api/reference.md"

    # Verify headers included API key
    assert client.calls[0]["headers"]["X-API-Key"] == "test-key"

    # Fetch
    doc = await provider.fetch("docs/concepts.md")
    assert isinstance(doc, KnowledgeDocument)
    assert doc.ref == "docs/concepts.md"
    assert doc.title == "Core Concepts"
    assert "distinct from memory" in doc.content

    # Verify the fetch call included the API key
    assert client.calls[1]["headers"]["X-API-Key"] == "test-key"


async def test_fetch_not_found_raises() -> None:
    """LLM-Wiki fetch with 404 raises KnowledgeNotFound."""
    from waywarden.adapters.knowledge.filesystem import KnowledgeNotFound
    from waywarden.adapters.knowledge.llm_wiki import LLMWikiKnowledgeProvider

    client = CassetteWikiClient([{"ref": "a.md", "snippet": ""}], None, fetch_status=404)
    provider = LLMWikiKnowledgeProvider(
        endpoint="http://localhost:9999",
        api_key="my-key",
        client=client,
    )

    with pytest.raises(KnowledgeNotFound, match="not found"):
        await provider.fetch("missing.md")


async def test_empty_result_from_search() -> None:
    """LLM-Wiki returns empty list when no results."""
    from waywarden.adapters.knowledge.llm_wiki import LLMWikiKnowledgeProvider

    client = CassetteWikiClient([], None)
    provider = LLMWikiKnowledgeProvider(endpoint="http://localhost:9999", client=client)

    results = await provider.search("nonexistent-term")
    assert results == []
