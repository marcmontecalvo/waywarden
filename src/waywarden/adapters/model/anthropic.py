"""Anthropic model provider adapter."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from importlib import import_module
from typing import Protocol, cast

from waywarden.domain.providers.types.model import ModelCompletion, PromptEnvelope
from waywarden.domain.providers.types.tool import ToolDecl


class _AnthropicMessages(Protocol):
    async def create(self, **kwargs: object) -> object: ...


class _AnthropicClient(Protocol):
    messages: _AnthropicMessages


class AnthropicModelProvider:
    """ModelProvider implementation backed by Anthropic Messages API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "claude-3-5-sonnet-latest",
        max_tokens: int = 1024,
        client: _AnthropicClient | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("api_key must not be empty")
        if not model.strip():
            raise ValueError("model must not be empty")
        if max_tokens < 1:
            raise ValueError("max_tokens must be >= 1")

        self._model = model
        self._max_tokens = max_tokens
        self._client = client or self._build_client(api_key)

    async def complete(
        self,
        prompt: PromptEnvelope,
        *,
        tools: Sequence[ToolDecl] = (),
        stream: bool = False,
    ) -> ModelCompletion:
        if stream:
            raise NotImplementedError("AnthropicModelProvider does not implement streaming yet")

        request = self._build_request(prompt, tools)
        response = await self._client.messages.create(**request)
        text = self._extract_text(response)
        prompt_tokens = self._usage_int(response, "input_tokens")
        completion_tokens = self._usage_int(response, "output_tokens")
        model = self._model_name(response)
        return ModelCompletion(
            session_id=prompt.session_id,
            text=text,
            model=model,
            provider="anthropic",
            recorded_at=datetime.now(UTC),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )

    def _build_client(self, api_key: str) -> _AnthropicClient:
        module = import_module("anthropic")
        client_cls = module.__dict__["AsyncAnthropic"]
        return cast(_AnthropicClient, client_cls(api_key=api_key))

    def _build_request(
        self,
        prompt: PromptEnvelope,
        tools: Sequence[ToolDecl],
    ) -> dict[str, object]:
        request: dict[str, object] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": [{"role": "user", "content": "\n".join(prompt.messages)}],
        }
        if prompt.system_prompt:
            request["system"] = prompt.system_prompt
        if tools:
            request["tools"] = [self._tool_decl(tool) for tool in tools]
        return request

    def _tool_decl(self, tool: ToolDecl) -> dict[str, object]:
        input_schema: object = tool.parameters or {"type": "object", "properties": {}}
        return {
            "name": tool.tool_id,
            "description": tool.description,
            "input_schema": input_schema,
        }

    def _extract_text(self, response: object) -> str:
        content = self._field(response, "content")
        if isinstance(content, str):
            return content
        if isinstance(content, Sequence) and not isinstance(content, (str, bytes, bytearray)):
            parts: list[str] = []
            for block in content:
                if self._field(block, "type") == "text":
                    text = self._field(block, "text")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts)
        return ""

    def _usage_int(self, response: object, key: str) -> int:
        usage = self._field(response, "usage")
        value = self._field(usage, key)
        if isinstance(value, int):
            return value
        return 0

    def _model_name(self, response: object) -> str:
        value = self._field(response, "model")
        if isinstance(value, str) and value.strip():
            return value
        return self._model

    def _field(self, value: object, key: str) -> object:
        if isinstance(value, Mapping):
            return value.get(key)
        return getattr(value, key, None)
