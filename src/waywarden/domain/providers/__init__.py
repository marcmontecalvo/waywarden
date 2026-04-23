"""Provider-neutral protocol definitions for Waywarden's adapter layer.

Every Protocol is ``@runtime_checkable`` so that concrete adapters can be
validated at startup without importing provider SDKs.

See ADR-0001 (context), ADR-0003 (memory vs knowledge), ADR-0005 (approval
model), and ADR-0011 (harness boundaries).
"""

from __future__ import annotations

from waywarden.domain.providers.channel import ChannelProvider
from waywarden.domain.providers.knowledge import KnowledgeProvider
from waywarden.domain.providers.memory import MemoryProvider
from waywarden.domain.providers.model import ModelProvider
from waywarden.domain.providers.tool import ToolProvider
from waywarden.domain.providers.tracer import TracerProvider

__all__ = [
    "ChannelProvider",
    "KnowledgeProvider",
    "MemoryProvider",
    "ModelProvider",
    "ToolProvider",
    "TracerProvider",
]
