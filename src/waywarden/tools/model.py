"""Re-export canonical provider types for tool registry consumers.

The registry works against the canonical ``ToolProvider`` protocol and
``ToolResult`` value type from the domain layer so that provider-neutral
type discipline is maintained.
"""

from __future__ import annotations

from waywarden.domain.providers.tool import ToolProvider
from waywarden.domain.providers.types.tool import ToolResult

__all__ = ["ToolProvider", "ToolResult"]
