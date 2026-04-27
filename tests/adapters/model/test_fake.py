"""Tests for the deterministic in-repo fake model provider."""

from __future__ import annotations

from waywarden.adapters.model.fake import FakeModelProvider
from waywarden.domain.ids import SessionId
from waywarden.domain.providers import ModelProvider
from waywarden.domain.providers.types.model import PromptEnvelope
from waywarden.domain.providers.types.tool import ToolDecl


async def test_deterministic_output() -> None:
    provider = FakeModelProvider()
    prompt = PromptEnvelope(
        session_id=SessionId("session-1"),
        messages=["Summarize the harness."],
    )

    first = await provider.complete(prompt)
    second = await provider.complete(prompt)

    assert first.text == second.text
    assert first.model == second.model
    assert first.provider == second.provider
    assert first.prompt_tokens == second.prompt_tokens
    assert first.completion_tokens == second.completion_tokens
    assert first.total_tokens == second.total_tokens
    assert first.provider == "fake"
    assert first.model == "fake-model"
    assert first.total_tokens == first.prompt_tokens + first.completion_tokens
    assert isinstance(provider, ModelProvider)


async def test_declarative_tool_script_changes_output() -> None:
    provider = FakeModelProvider(
        tool_script={
            ("filesystem", "read"): "scripted filesystem read result",
        }
    )
    prompt = PromptEnvelope(
        session_id=SessionId("session-1"),
        messages=["Use the filesystem tool."],
    )
    tools = [
        ToolDecl(
            tool_id="filesystem",
            action="read",
            description="Read a file from the workspace",
        )
    ]

    completion = await provider.complete(prompt, tools=tools)

    assert completion.text == "scripted filesystem read result"
