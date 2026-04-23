"""Test that MemoryProvider and KnowledgeProvider do not share a base Protocol.

ADR-0003 requires memory and knowledge to stay distinct.
"""

from __future__ import annotations

from typing import Generic, Protocol

from waywarden.domain.providers.knowledge import KnowledgeProvider
from waywarden.domain.providers.memory import MemoryProvider


def test_no_shared_base() -> None:
    """MemoryProvider and KnowledgeProvider must share only Protocol, Generic,
    and object in their MRO — no shared base class or Protocol."""
    memory_bases = set(MemoryProvider.__mro__)
    knowledge_bases = set(KnowledgeProvider.__mro__)

    shared = memory_bases & knowledge_bases
    allowed = {
        MemoryProvider,
        KnowledgeProvider,
        Protocol,
        Generic,
        object,
    }

    extra = shared - allowed
    assert not extra, f"MemoryProvider and KnowledgeProvider share unexpected bases: {extra}"
