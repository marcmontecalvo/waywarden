"""Value types for the channel provider protocol."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChannelMessage:
    """A message sent through a channel provider."""

    channel_name: str
    content: str
    metadata: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.content, str):
            raise TypeError("content must be a string")
        if self.metadata is not None and not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dict or None")


@dataclass(frozen=True, slots=True)
class ChannelSendResult:
    """Result of sending a message through a channel."""

    channel_name: str
    delivered: bool
    message_id: str | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.channel_name, str):
            raise TypeError("channel_name must be a string")
        if self.error is not None and not isinstance(self.error, str):
            raise TypeError("error must be a string or None")
