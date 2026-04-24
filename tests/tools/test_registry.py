"""Tests for ToolRegistry."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from waywarden.domain.manifest.tool_policy import ToolDecisionRule, ToolPolicy
from waywarden.domain.providers.types.tool import ToolResult
from waywarden.tools.builtin.shell_read import ShellReadTool
from waywarden.tools.errors import (
    DuplicateCapabilityError,
    UncoveredCapabilityError,
    UnknownCapabilityError,
)
from waywarden.tools.model import ToolProvider
from waywarden.tools.registry import ToolRegistry


class _FakeProviderA(ToolProvider):
    """Provider that owns capability 'alpha'."""

    def capabilities(self) -> frozenset[str]:
        return frozenset(("alpha",))

    async def invoke(self, tool_id: str, action: str, params: Mapping[str, Any]) -> ToolResult:
        return ToolResult(tool_id=tool_id, action=action, output=f"alpha:{action}", success=True)


class _FakeProviderB(ToolProvider):
    """Provider that owns capability 'beta'."""

    def capabilities(self) -> frozenset[str]:
        return frozenset(("beta",))

    async def invoke(self, tool_id: str, action: str, params: Mapping[str, Any]) -> ToolResult:
        return ToolResult(tool_id=tool_id, action=action, output=f"beta:{action}", success=True)


class _FakeProviderC(ToolProvider):
    """Provider that owns 'alpha' to test duplicate detection."""

    def capabilities(self) -> frozenset[str]:
        return frozenset(("alpha",))

    async def invoke(self, tool_id: str, action: str, params: Mapping[str, Any]) -> ToolResult:
        return ToolResult(tool_id=tool_id, action=action, output=f"c:{action}", success=True)


@pytest.mark.asyncio
async def test_dispatch_to_owner_executes() -> None:
    """ToolRegistry.invoke dispatches to the correct provider and returns result."""
    registry = ToolRegistry([_FakeProviderA()])
    result = await registry.invoke("alpha", "do", {})
    assert result.success is True
    assert result.output == "alpha:do"


@pytest.mark.asyncio
async def test_unknown_capability_raises() -> None:
    """Invoking a capability no provider owns raises UnknownCapabilityError."""
    registry = ToolRegistry([_FakeProviderA()])

    with pytest.raises(UnknownCapabilityError) as exc:
        await registry.invoke("nonexistent", "go", {})

    assert "nonexistent" in str(exc.value)


def test_duplicate_capability_rejected() -> None:
    """Two providers claiming the same capability raises DuplicateCapabilityError."""
    with pytest.raises(DuplicateCapabilityError) as exc:
        ToolRegistry([_FakeProviderA(), _FakeProviderC()])

    assert "alpha" in str(exc.value)


def test_validate_against_policy_catches_uncovered() -> None:
    """validate_against_policy raises for rules referencing unknown tools."""
    registry = ToolRegistry([_FakeProviderA()])

    policy = ToolPolicy(
        preset="ask",
        rules=[
            ToolDecisionRule(tool="alpha", action="do", decision="approval-required"),
            ToolDecisionRule(tool="nonexistent", action="do", decision="auto-allow"),
        ],
        default_decision="auto-allow",
    )

    with pytest.raises(UncoveredCapabilityError) as exc:
        registry.validate_against_policy(policy)

    assert "nonexistent" in str(exc.value)


def test_validate_against_policy_passes_for_covered() -> None:
    """validate_against_policy succeeds when all tools are covered."""
    registry = ToolRegistry([_FakeProviderA(), _FakeProviderB()])

    policy = ToolPolicy(
        preset="ask",
        rules=[
            ToolDecisionRule(tool="alpha", action="do", decision="approval-required"),
            ToolDecisionRule(tool="beta", action="undo", decision="auto-allow"),
        ],
        default_decision="approval-required",
    )

    # Should not raise
    registry.validate_against_policy(policy)


def test_shell_read_tool_in_registry() -> None:
    """ShellReadTool can be registered and its capability is recognized."""
    shell = ShellReadTool(command_handler={"echo test": "test\n"})
    registry = ToolRegistry([shell])
    assert "shell" in registry._providers


@pytest.mark.asyncio
async def test_shell_read_tool_in_registry_executes() -> None:
    """ShellReadTool in registry returns expected content."""
    shell = ShellReadTool(command_handler={"echo test": "test\n"})
    registry = ToolRegistry([shell])
    result = await registry.invoke("shell", "read", {"command": "echo test"})
    assert result.success is True
    assert result.output == "test\n"
