from typing import Protocol


class ToolProvider(Protocol):
    async def invoke(self, call: dict[str, object]) -> dict[str, object]: ...
