"""Value types for the tool provider protocol."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ToolDecl:
    """Declaration of a tool available for model invocation."""

    tool_id: str
    action: str
    description: str
    parameters: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        if not self.tool_id.strip():
            raise ValueError("tool_id must not be empty")
        if not self.action.strip():
            raise ValueError("action must not be empty")
        if not isinstance(self.description, str):
            raise TypeError("description must be a string")


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Result of invoking a tool."""

    tool_id: str
    action: str
    output: str
    success: bool = True
    error: str | None = None

    def __post_init__(self) -> None:
        if not self.tool_id.strip():
            raise ValueError("tool_id must not be empty")
        if not self.action.strip():
            raise ValueError("action must not be empty")
        if not isinstance(self.output, str):
            raise TypeError("output must be a string")
        if self.error is not None and not isinstance(self.error, str):
            raise TypeError("error must be a string or None")
