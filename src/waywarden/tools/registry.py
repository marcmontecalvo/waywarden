"""Tool registry.

Maps capability ids to concrete ``ToolProvider`` implementations and
dispatches invocations.  Validates that every capability referenced by a
tool policy is backed by a registered provider.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from waywarden.domain.manifest.tool_policy import ToolPolicy
from waywarden.tools.errors import (
    DuplicateCapabilityError,
    UncoveredCapabilityError,
    UnknownCapabilityError,
)
from waywarden.tools.model import ToolProvider, ToolResult


class ToolRegistry:
    """Registry that maps capability ids to provider instances.

    Parameters:
        providers: Ordered list of provider instances.  The first provider
            to claim a capability wins; duplicates are rejected.

    Raises:
        DuplicateCapabilityError: If two providers claim the same capability.
    """

    def __init__(self, providers: Sequence[ToolProvider]) -> None:
        self._providers: dict[str, ToolProvider] = {}
        for provider in providers:
            for cap in provider.capabilities():
                if cap in self._providers:
                    raise DuplicateCapabilityError(cap)
                self._providers[cap] = provider

    async def invoke(
        self, tool_id: str, action: str, params: Mapping[str, object] | None = None
    ) -> ToolResult:
        """Dispatch to the provider owning ``tool_id``.

        Parameters:
            tool_id: Capability id to invoke.
            action: Action string (e.g. ``read``, ``write``).
            params: Optional parameters passed to the provider.  If omitted,
                an empty dict is used.

        Raises:
            UnknownCapabilityError: If no provider owns ``tool_id``.
        """
        provider = self._providers.get(tool_id)
        if provider is None:
            raise UnknownCapabilityError(tool_id)
        return await provider.invoke(tool_id, action, params or {})

    def validate_against_policy(self, policy: ToolPolicy) -> None:
        """Validate that every tool capability referenced by a policy is registered.

        Raises:
            UncoveredCapabilityError: If any rule's ``tool`` is not owned by
                a registered provider.
        """
        for rule in policy.rules:
            if rule.tool not in self._providers:
                raise UncoveredCapabilityError(rule.tool)
