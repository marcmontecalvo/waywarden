"""Deterministic in-repo model provider for tests and local development."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from waywarden.domain.providers.types.model import ModelCompletion, PromptEnvelope
from waywarden.domain.providers.types.tool import ToolDecl

ToolScript = Mapping[tuple[str, str], str]


class FakeModelProvider:
    """A deterministic model provider with optional scripted tool responses."""

    def __init__(
        self,
        *,
        model: str = "fake-model",
        provider: str = "fake",
        scripted_outputs: Mapping[str, str] | None = None,
        tool_script: ToolScript | None = None,
    ) -> None:
        self._model = model
        self._provider = provider
        self._scripted_outputs = dict(scripted_outputs or {})
        self._tool_script = dict(tool_script or {})

    async def complete(
        self,
        prompt: PromptEnvelope,
        *,
        tools: Sequence[ToolDecl] = (),
        stream: bool = False,
    ) -> ModelCompletion:
        if stream:
            raise NotImplementedError("FakeModelProvider does not implement streaming")

        text = self._scripted_tool_output(tools)
        if text is None:
            key = "\n".join(prompt.messages)
            text = self._scripted_outputs.get(key)
        if text is None:
            text = f"fake-response-{self._prompt_digest(prompt, tools)}"

        prompt_tokens = self._count_prompt_tokens(prompt, tools)
        completion_tokens = max(1, len(text.split()))
        return ModelCompletion(
            session_id=prompt.session_id,
            text=text,
            model=self._model,
            provider=self._provider,
            recorded_at=datetime.now(UTC),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )

    def _scripted_tool_output(self, tools: Sequence[ToolDecl]) -> str | None:
        for tool in tools:
            output = self._tool_script.get((tool.tool_id, tool.action))
            if output is not None:
                return output
        return None

    def _prompt_digest(self, prompt: PromptEnvelope, tools: Sequence[ToolDecl]) -> str:
        payload = {
            "messages": prompt.messages,
            "system_prompt": prompt.system_prompt,
            "tools": prompt.tools,
            "declared_tools": [
                {
                    "tool_id": tool.tool_id,
                    "action": tool.action,
                    "description": tool.description,
                    "parameters": dict(tool.parameters or {}),
                }
                for tool in tools
            ],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()[:16]

    def _count_prompt_tokens(self, prompt: PromptEnvelope, tools: Sequence[ToolDecl]) -> int:
        text_parts = list(prompt.messages)
        if prompt.system_prompt:
            text_parts.append(prompt.system_prompt)
        for tool in tools:
            text_parts.extend((tool.tool_id, tool.action, tool.description))
        return max(1, sum(len(part.split()) for part in text_parts))
