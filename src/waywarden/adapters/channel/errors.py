"""Channel adapter error types."""

from __future__ import annotations


class ChannelTransportError(Exception):
    """Raised when a channel transport operation fails."""

    def __init__(self, message: str, *, original: Exception | None = None) -> None:
        super().__init__(message)
        self.original = original


class ChannelRejectedError(Exception):
    """Raised when the destination rejects the message."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
