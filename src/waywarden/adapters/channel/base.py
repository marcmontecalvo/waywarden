"""Channel adapter base class.

Provides a shared abstract base for channel adapters that bind transport
to domain calls.  Channel adapters must never access repositories directly —
business logic belongs in orchestrators / services, not adapters.

See ADR-0011 for adapter boundary rules.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from waywarden.domain.providers.channel import ChannelProvider

if TYPE_CHECKING:
    from waywarden.domain.providers.types.channel import ChannelMessage, ChannelSendResult


class ChannelAdapterBase(ABC, ChannelProvider):
    """Abstract base for channel adapters.

    Parameters
    ----------
    name:
        Stable identifier for this channel (e.g. ``"web"``).
    """

    def __init__(self, name: str) -> None:
        self._name = name
        self._logger: logging.Logger | None = None

    @abstractmethod
    async def send(self, message: ChannelMessage) -> ChannelSendResult: ...

    def name(self) -> str:
        return self._name

    def _setup_logger(self) -> logging.Logger:
        """Instantiate the adapter-local logger.

        Returns the logger so callers can propagate structured fields.
        """
        if self._logger is None:
            self._logger = logging.getLogger(f"waywarden.channel.{self._name}")
        return self._logger
