"""Channel provider protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from waywarden.domain.providers.types.channel import ChannelMessage, ChannelSendResult


@runtime_checkable
class ChannelProvider(Protocol):
    """Protocol for channel providers."""

    async def send(self, message: ChannelMessage) -> ChannelSendResult: ...

    def name(self) -> str: ...
