"""LLM-Wiki knowledge provider adapter.

HTTP adapter against the LLM-Wiki service.
"""

from __future__ import annotations

import json
from typing import Protocol

from waywarden.domain.providers.types.knowledge import (
    KnowledgeDocument,
    KnowledgeHit,
)


class _LlmWikiClient(Protocol):
    """Minimal HTTP client protocol to avoid hard dependency."""

    async def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> _LlmWikiResponse: ...


class _LlmWikiResponse(Protocol):
    status_code: int

    async def text(self) -> str: ...


class LLMWikiKnowledgeProvider:
    """KnowledgeProvider backed by the LLM-Wiki service."""

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str | None = None,
        client: _LlmWikiClient | None = None,
    ) -> None:
        if not endpoint.strip():
            raise ValueError("endpoint must not be empty")

        self._endpoint = endpoint.rstrip("/")
        self._api_key = api_key
        self._client = client

    async def search(
        self,
        query: str,
        *,
        limit: int = 10,
    ) -> list[KnowledgeHit]:
        assert self._client is not None
        url = f"{self._endpoint}/wiki/search?q={query}&limit={limit}"
        headers = self._headers()
        response = await self._client.get(url, headers=headers)

        if response.status_code == 404:
            return []

        payload = json.loads(await response.text())
        results: list[KnowledgeHit] = []
        for item in payload:
            results.append(
                KnowledgeHit(
                    ref=item.get("ref", ""),
                    title=item.get("title", ""),
                    snippet=item.get("snippet", ""),
                    score=1.0,
                )
            )
        return results

    async def fetch(self, ref: str) -> KnowledgeDocument:
        assert self._client is not None
        url = f"{self._endpoint}/wiki/fetch?ref={ref}"
        headers = self._headers()
        response = await self._client.get(url, headers=headers)

        if response.status_code == 404:
            from waywarden.adapters.knowledge.filesystem import (
                KnowledgeNotFound,
            )

            raise KnowledgeNotFound(f"knowledge document not found: {ref}")

        payload = json.loads(await response.text())
        return KnowledgeDocument(
            ref=payload.get("ref", ref),
            title=payload.get("title", ""),
            content=payload.get("content", ""),
        )

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/json",
        }
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        return headers
