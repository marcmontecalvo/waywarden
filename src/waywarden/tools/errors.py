"""Tool registry exceptions.

Each exception is a distinct type so callers can catch exactly what they need.
"""

from __future__ import annotations


class ToolError(RuntimeError):
    """Base exception for all tool registry errors."""


class DuplicateCapabilityError(ToolError):
    """Raised when two providers claim the same capability id."""

    def __init__(self, capability_id: str) -> None:
        super().__init__(f"duplicate capability: {capability_id!r}")


class UnknownCapabilityError(ToolError):
    """Raised when ``invoke`` is called with a capability id not owned by any provider."""

    def __init__(self, capability_id: str) -> None:
        super().__init__(f"unknown capability: {capability_id!r}")


class UncoveredCapabilityError(ToolError):
    """Raised when validate_against_policy finds a rule referencing a tool
    that no provider owns."""

    def __init__(self, tool_id: str, action: str | None = None) -> None:
        desc = f"{tool_id}"
        if action:
            desc = f"{tool_id}.{action}" if len(action) > 0 else tool_id
        super().__init__(f"uncovered capability in policy rule: {desc!r}")
