"""Provider-neutral value types for the provider protocol layer.

All value types are frozen dataclasses with slots for memory efficiency.
No provider SDK types leak into this package.
"""

from __future__ import annotations

from waywarden.domain.providers.types.channel import (
    ChannelMessage,
    ChannelSendResult,
)
from waywarden.domain.providers.types.knowledge import (
    KnowledgeDocument,
    KnowledgeHit,
)
from waywarden.domain.providers.types.memory import (
    MemoryEntry,
    MemoryEntryRef,
    MemoryQuery,
)
from waywarden.domain.providers.types.model import (
    ModelCompletion,
    PromptEnvelope,
)
from waywarden.domain.providers.types.tool import (
    ToolDecl,
    ToolResult,
)

__all__ = [
    "ChannelMessage",
    "ChannelSendResult",
    "KnowledgeDocument",
    "KnowledgeHit",
    "MemoryEntry",
    "MemoryEntryRef",
    "MemoryQuery",
    "ModelCompletion",
    "PromptEnvelope",
    "ToolDecl",
    "ToolResult",
]
