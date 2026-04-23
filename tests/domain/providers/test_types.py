"""Test that all provider value types are frozen dataclasses."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from waywarden.domain.providers.types.channel import ChannelMessage, ChannelSendResult
from waywarden.domain.providers.types.knowledge import KnowledgeDocument, KnowledgeHit
from waywarden.domain.providers.types.memory import MemoryEntry, MemoryEntryRef, MemoryQuery
from waywarden.domain.providers.types.model import ModelCompletion, PromptEnvelope
from waywarden.domain.providers.types.tool import ToolDecl, ToolResult


def _assert_frozen(cls: type) -> None:
    """Verify the dataclass was declared with frozen=True."""
    params = getattr(cls, "__dataclass_params__", None)
    assert params is not None, f"{cls.__name__} is not a dataclass"
    assert params.frozen, f"{cls.__name__} must be frozen"


def test_value_types_are_frozen() -> None:
    """All value types must be frozen dataclasses."""
    for cls in (
        PromptEnvelope,
        ModelCompletion,
        MemoryEntry,
        MemoryEntryRef,
        MemoryQuery,
        KnowledgeHit,
        KnowledgeDocument,
        ToolDecl,
        ToolResult,
        ChannelMessage,
        ChannelSendResult,
    ):
        _assert_frozen(cls)


def test_prompt_envelope_rejects_empty_session() -> None:
    with pytest.raises(ValueError, match="session_id"):
        PromptEnvelope(session_id="", messages=["hello"])


def test_prompt_envelope_rejects_empty_messages() -> None:
    with pytest.raises(ValueError, match="messages"):
        PromptEnvelope(session_id="s1", messages=[])


def test_model_completion_rejects_negative_tokens() -> None:
    with pytest.raises(ValueError, match="token counts"):
        ModelCompletion(
            session_id="s1",
            text="hi",
            model="test",
            provider="test",
            recorded_at=datetime.now(UTC),
            prompt_tokens=-1,
        )


def test_model_completion_rejects_mismatched_total() -> None:
    with pytest.raises(ValueError, match="total_tokens"):
        ModelCompletion(
            session_id="s1",
            text="hi",
            model="test",
            provider="test",
            recorded_at=datetime.now(UTC),
            prompt_tokens=5,
            completion_tokens=3,
            total_tokens=100,
        )


def test_memory_entry_autosets_created_at() -> None:
    entry = MemoryEntry(session_id="s1", content="hello")
    assert entry.created_at is not None


def test_tool_decl_rejects_empty_tool_id() -> None:
    with pytest.raises(ValueError, match="tool_id"):
        ToolDecl(tool_id="", action="run", description="test")


def test_tool_result_defaults_success() -> None:
    result = ToolResult(tool_id="t1", action="run", output="ok")
    assert result.success is True
    assert result.error is None
