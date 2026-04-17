from typing import Protocol


class ChannelProvider(Protocol):
    async def receive(self, payload: dict[str, object]) -> dict[str, object]: ...
