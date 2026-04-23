"""Tool provider protocol."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from waywarden.domain.providers.types.tool import ToolResult


@runtime_checkable
class ToolProvider(Protocol):
    """Protocol for tool providers."""

    async def invoke(
        self,
        tool_id: str,
        action: str,
        params: Mapping[str, object],
    ) -> ToolResult: ...

    def capabilities(self) -> frozenset[str]: ...
