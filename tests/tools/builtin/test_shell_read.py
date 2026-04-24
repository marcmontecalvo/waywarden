"""Tests for ShellReadTool builtin."""

import pytest

from waywarden.domain.providers.types.tool import ToolResult
from waywarden.tools.builtin.shell_read import ShellReadTool


@pytest.mark.asyncio
async def test_shell_read_returns_expected_output() -> None:
    """ShellReadTool with a command_handler returns the expected text."""
    handler = {"echo hello": "hello\n", "echo goodbye": "goodbye\n"}
    tool = ShellReadTool(command_handler=handler)

    result = await tool.invoke("shell", "read", {"command": "echo hello"})

    assert isinstance(result, ToolResult)
    assert result.success is True
    assert result.output == "hello\n"


@pytest.mark.asyncio
async def test_shell_read_capabilities() -> None:
    """ShellReadTool declares the 'shell' capability."""
    tool = ShellReadTool()
    caps = tool.capabilities()
    assert caps == frozenset(("shell",))


@pytest.mark.asyncio
async def test_shell_read_unsupported_action() -> None:
    """ShellReadTool rejects unsupported actions gracefully."""
    tool = ShellReadTool()

    result = await tool.invoke("shell", "write", {"command": "echo test"})

    assert isinstance(result, ToolResult)
    assert result.success is False
    assert "unsupported action" in result.error  # noqa: SIM300
