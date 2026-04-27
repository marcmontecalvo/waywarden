"""Cassette-backed tests for the Anthropic model adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from waywarden.adapters.model.anthropic import AnthropicModelProvider
from waywarden.domain.ids import SessionId
from waywarden.domain.providers import ModelProvider
from waywarden.domain.providers.types.model import PromptEnvelope


class CassetteMessages:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return self.payload


class CassetteClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.messages = CassetteMessages(payload)


async def test_roundtrip_with_cassette() -> None:
    cassette = Path(__file__).parent / "cassettes" / "anthropic_roundtrip.json"
    payload = json.loads(cassette.read_text(encoding="utf-8"))
    client = CassetteClient(payload)
    provider = AnthropicModelProvider(api_key="test-key", client=cast(Any, client))
    prompt = PromptEnvelope(
        session_id=SessionId("session-1"),
        messages=["Return the deterministic cassette response."],
        system_prompt="You are a test assistant.",
    )

    completion = await provider.complete(prompt)

    assert completion.text == "Cassette response from Anthropic."
    assert completion.provider == "anthropic"
    assert completion.model == payload["model"]
    assert completion.prompt_tokens == payload["usage"]["input_tokens"]
    assert completion.completion_tokens == payload["usage"]["output_tokens"]
    assert isinstance(provider, ModelProvider)
    assert client.messages.calls[0]["system"] == "You are a test assistant."
