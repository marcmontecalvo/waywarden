"""Provider factory — resolve concrete adapters from config strings.

This module provides functions that instantiate provider adapters
based on a string identifier (the ``model_router``, ``memory_provider``,
or ``knowledge_provider`` value from ``AppConfig``).  The mapping is
a plain dict so the test body never needs conditional imports of
adapter modules.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import SecretStr

from waywarden.adapters.knowledge.filesystem import FilesystemKnowledgeProvider
from waywarden.adapters.knowledge.llm_wiki import LLMWikiKnowledgeProvider
from waywarden.adapters.memory import FakeMemoryProvider, HonchoMemoryProvider
from waywarden.domain.providers import KnowledgeProvider, MemoryProvider

__all__ = [
    "build_memory_provider",
    "build_knowledge_provider",
]


def _to_str(value: Any) -> str:
    """Coerce a config value to a plain str (handles SecretStr)."""
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    return str(value) if value else ""


def build_memory_provider(
    provider_type: str,
    conf: Mapping[str, Any],
) -> MemoryProvider:
    """Build a MemoryProvider from a config string.

    Parameters
    ----------
    provider_type:
        One of ``"fake"``, ``"honcho"``, etc.
    conf:
        App-level config mapping with at least the keys needed for
        the selected provider type.

    Returns
    -------
    MemoryProvider
        A concrete in-memory or honcho-backed memory provider.
    """
    _FACTORY: dict[str, Any] = {
        "fake": lambda c: FakeMemoryProvider(),
        "honcho": lambda c: HonchoMemoryProvider(
            endpoint=_to_str(c.get("honcho_endpoint")),
            api_key=_to_str(c.get("honcho_api_key")),
            client=c.get("_client"),
        ),
    }

    builder = _FACTORY.get(provider_type)
    if builder is None:
        raise ValueError(
            f"unknown memory provider type {provider_type!r}; expected one of {sorted(_FACTORY)}"
        )
    return builder(conf)  # type: ignore[no-any-return]


def build_knowledge_provider(
    provider_type: str,
    conf: Mapping[str, Any],
) -> KnowledgeProvider:
    """Build a KnowledgeProvider from a config string.

    Parameters
    ----------
    provider_type:
        One of ``"filesystem"``, ``"llm_wiki"``, etc.
    conf:
        App-level config mapping with at least the keys needed.

    Returns
    -------
    KnowledgeProvider
        A concrete knowledge provider.
    """
    _FACTORY: dict[str, Any] = {
        "filesystem": lambda c: FilesystemKnowledgeProvider(
            Path(str(c.get("knowledge_filesystem_root", "assets/knowledge")))
        ),
        "llm_wiki": lambda c: LLMWikiKnowledgeProvider(
            endpoint=c.get("llm_wiki_endpoint") or "",
            api_key=_to_str(c.get("llm_wiki_api_key")) if c.get("llm_wiki_api_key") else None,
            client=c.get("_client"),
        ),
    }

    builder = _FACTORY.get(provider_type)
    if builder is None:
        raise ValueError(
            f"unknown knowledge provider type {provider_type!r}; expected one of {sorted(_FACTORY)}"
        )
    return builder(conf)  # type: ignore[no-any-return]
