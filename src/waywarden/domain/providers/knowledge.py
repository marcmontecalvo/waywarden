"""Knowledge provider protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from waywarden.domain.providers.types.knowledge import KnowledgeDocument, KnowledgeHit


@runtime_checkable
class KnowledgeProvider(Protocol):
    """Protocol for knowledge providers.

    Memory and knowledge are kept distinct (ADR-0003): this Protocol
    does not inherit from any shared base.
    """

    async def search(
        self,
        query: str,
        *,
        limit: int = 10,
    ) -> list[KnowledgeHit]: ...

    async def fetch(self, ref: str) -> KnowledgeDocument: ...
