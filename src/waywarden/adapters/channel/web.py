"""Web channel adapter.

Delivers messages to an HTTP webhook configured in ``AppConfig``.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from waywarden.adapters.channel.base import ChannelAdapterBase
from waywarden.adapters.channel.errors import ChannelRejectedError
from waywarden.domain.providers.types.channel import ChannelMessage, ChannelSendResult

logger = logging.getLogger("waywarden.channel.web")


class WebChannel(ChannelAdapterBase):
    """Sends channel messages via HTTP POST to a webhook URL.

    Parameters
    ----------
    webhook_url:
        The target URL for delivering messages.
    timeout:
        Request timeout in seconds (default 5).
    """

    CHANNEL_NAME = "web"

    def __init__(self, webhook_url: str, *, timeout: float = 5.0) -> None:
        super().__init__(name=self.CHANNEL_NAME)
        self._webhook_url = webhook_url
        self._timeout = timeout
        self._client = httpx.AsyncClient(timeout=self._timeout)

    async def send(self, message: ChannelMessage) -> ChannelSendResult:
        if message.channel_name != self._name:
            raise ChannelRejectedError(
                f"message channel {message.channel_name!r} does not match adapter {self._name!r}"
            )

        payload: dict[str, Any] = {
            "content": message.content,
        }
        if message.metadata:
            payload["metadata"] = message.metadata

        try:
            response = await self._client.post(
                self._webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
        except httpx.RequestError as exc:
            logger.warning("web transport error posting to %s: %s", self._webhook_url, exc)
            return ChannelSendResult(
                channel_name=self._name,
                delivered=False,
                error=str(exc),
            )

        if response.status_code == 200:
            return ChannelSendResult(
                channel_name=self._name,
                delivered=True,
                message_id=str(response.status_code),
            )

        if 400 <= response.status_code < 500:
            raise ChannelRejectedError(f"webhook rejected message: {response.status_code}")

        return ChannelSendResult(
            channel_name=self._name,
            delivered=False,
            error=f"unexpected status {response.status_code}",
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    def __del__(self) -> None:
        """Best-effort cleanup of the underlying HTTP client on GC."""
        try:
            if not hasattr(self, "_client"):
                return
            if getattr(self._client, "is_closed", True):
                return
        except Exception:  # pragma: no cover
            pass
