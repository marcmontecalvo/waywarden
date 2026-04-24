"""Built-in shell read tool provider.

Capability id: ``shell``
Supported actions: ``read``
"""

from __future__ import annotations

import asyncio
from typing import Any

from waywarden.domain.providers.types.tool import ToolResult
from waywarden.tools.model import ToolProvider


class ShellReadTool(ToolProvider):
    """Read-only shell tool provider.

    Supports action ``read`` which executes a shell command and returns
    its combined stdout/stderr output.
    """

    def __init__(
        self,
        command_handler: dict[str, str] | None = None,
    ) -> None:
        """
        Parameters:
            command_handler: Optional mapping of test command strings to
                their expected output.  When provided, the tool returns the
                mapped value instead of spawning a real shell process.
        """
        self._handler: dict[str, str] | None = command_handler

    def capabilities(self) -> frozenset[str]:
        return frozenset(("shell",))

    async def invoke(self, tool_id: str, action: str, params: Any) -> ToolResult:
        if tool_id != "shell":
            return ToolResult(
                tool_id=tool_id,
                action=action,
                output="",
                success=False,
                error=f"unknown tool: {tool_id!r}",
            )

        if action == "read":
            cmd = _extract_command(params)
            if self._handler is not None:
                output = self._handler.get(cmd)
                if output is not None:
                    return ToolResult(tool_id="shell", action="read", output=output, success=True)
            return await _command_read(tool_id, action, cmd)

        return ToolResult(
            tool_id="shell",
            action=action,
            output="",
            success=False,
            error=f"unsupported action for tool 'shell': {action!r}",
        )


def _extract_command(params: Any) -> str:
    if not isinstance(params, dict):
        raise TypeError("params must be a mapping")
    cmd = params.get("command")
    if cmd is None:
        raise TypeError("missing 'command' parameter")
    if not isinstance(cmd, str):
        raise TypeError("'command' must be a string")
    return cmd


async def _command_read(tool_id: str, action: str, cmd: str) -> ToolResult:
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        out = stdout.decode() if stdout else ""
        err = stderr.decode() if stderr else ""
        combined = out + err
        return ToolResult(
            tool_id=tool_id,
            action=action,
            output=combined,
            success=proc.returncode == 0,
        )
    except FileNotFoundError:
        return ToolResult(
            tool_id=tool_id,
            action=action,
            output="",
            success=False,
            error=f"command not found: {cmd}",
        )
    except TimeoutError:
        return ToolResult(
            tool_id=tool_id,
            action=action,
            output="",
            success=False,
            error=f"command timed out: {cmd}",
        )
