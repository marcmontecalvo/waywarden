"""Tests for the web channel adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from waywarden.adapters.channel.base import ChannelAdapterBase
from waywarden.adapters.channel.errors import ChannelRejectedError
from waywarden.adapters.channel.web import WebChannel
from waywarden.domain.providers import ChannelProvider
from waywarden.domain.providers.types.channel import ChannelMessage


async def test_send_posts_to_webhook() -> None:
    webhook_url = "http://example.com/webhook"

    mock_response = httpx.Response(
        status_code=200,
        request=httpx.Request("POST", webhook_url),
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = True
        mock_client_cls.return_value = mock_client

        channel = WebChannel(webhook_url=webhook_url)

        message = ChannelMessage(channel_name="web", content="Hello")
        result = await channel.send(message)

        assert isinstance(channel, ChannelProvider)
        assert isinstance(channel, ChannelAdapterBase)
        assert channel.name() == "web"
        assert result.delivered is True
        assert result.error is None
        mock_client.post.assert_called_once_with(
            webhook_url,
            json={"content": "Hello"},
            headers={"Content-Type": "application/json"},
        )

        await channel.close()


async def test_send_with_metadata() -> None:
    webhook_url = "http://example.com/webhook"

    mock_response = httpx.Response(
        status_code=200,
        request=httpx.Request("POST", webhook_url),
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = True
        mock_client_cls.return_value = mock_client

        channel = WebChannel(webhook_url=webhook_url)

        message = ChannelMessage(
            channel_name="web",
            content="Hello",
            metadata={"source": "test"},
        )
        result = await channel.send(message)

        assert result.delivered is True
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["metadata"] == {"source": "test"}

        await channel.close()


async def test_transport_error_surfaces() -> None:
    webhook_url = "http://example.com/webhook"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.ConnectError("connection refused")
        )
        mock_client.is_closed = True
        mock_client_cls.return_value = mock_client

        channel = WebChannel(webhook_url=webhook_url)

        message = ChannelMessage(channel_name="web", content="Hello")
        result = await channel.send(message)

        assert result.delivered is False
        assert result.error == "connection refused"

        await channel.close()


async def test_rejected_error_on_4xx() -> None:
    webhook_url = "http://example.com/webhook"

    mock_response = httpx.Response(
        status_code=400,
        request=httpx.Request("POST", webhook_url),
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = True
        mock_client_cls.return_value = mock_client

        channel = WebChannel(webhook_url=webhook_url)

        message = ChannelMessage(channel_name="web", content="Hello")

        with pytest.raises(ChannelRejectedError, match="webhook rejected"):
            await channel.send(message)

        await channel.close()


async def test_unhandled_status_returns_failed_result() -> None:
    webhook_url = "http://example.com/webhook"

    mock_response = httpx.Response(
        status_code=503,
        request=httpx.Request("POST", webhook_url),
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = True
        mock_client_cls.return_value = mock_client

        channel = WebChannel(webhook_url=webhook_url)

        message = ChannelMessage(channel_name="web", content="Hello")
        result = await channel.send(message)

        assert result.delivered is False
        assert "503" in result.error if result.error else False

        await channel.close()


async def test_channel_name_mismatch_raises() -> None:
    channel = WebChannel(webhook_url="http://example.com/webhook")

    message = ChannelMessage(channel_name="slack", content="Hello")

    with pytest.raises(ChannelRejectedError, match="does not match adapter"):
        await channel.send(message)


async def test_implements_channel_provider() -> None:
    channel = WebChannel(webhook_url="http://example.com/webhook")
    assert isinstance(channel, ChannelProvider)
    assert isinstance(channel, ChannelAdapterBase)
    await channel.close()


async def test_channel_name_is_web() -> None:
    channel = WebChannel(webhook_url="http://example.com/webhook")
    assert channel.name() == "web"
    await channel.close()
