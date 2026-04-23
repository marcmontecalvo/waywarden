"""Value types for the knowledge provider protocol."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KnowledgeHit:
    """A single match returned by a knowledge search."""

    ref: str
    title: str
    snippet: str
    score: float


@dataclass(frozen=True, slots=True)
class KnowledgeDocument:
    """A full knowledge document fetched by reference."""

    ref: str
    title: str
    content: str
    metadata: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.content, str):
            raise TypeError("content must be a string")
        if self.metadata is not None and not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dict or None")
