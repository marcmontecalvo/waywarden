"""Adversarial red-team tests for P3-1 through P3-4 implementation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest

from waywarden.adapters.model.anthropic import AnthropicModelProvider
from waywarden.adapters.model.fake import FakeModelProvider
from waywarden.adapters.model.router import ModelRouter, UnknownModelProviderError
from waywarden.domain.ids import SessionId
from waywarden.domain.providers import ModelProvider
from waywarden.domain.providers.types.model import ModelCompletion, PromptEnvelope


async def test_fake_model_produces_different_output_for_different_inputs() -> None:
    """A stub always returns the same output regardless of input.

    The FakeModelProvider should produce different text for different prompts
    (deterministic hashing). If it somehow returns a constant it is a stub.
    """
    provider = FakeModelProvider()
    prompt_a = PromptEnvelope(session_id=SessionId("s1"), messages=["What is 1+1?"])
    prompt_b = PromptEnvelope(
        session_id=SessionId("s2"),
        messages=["What is the capital of France?"],
    )

    result_a = await provider.complete(prompt_a)
    result_b = await provider.complete(prompt_b)

    assert result_a.text != result_b.text, (
        "FakeModelProvider returned the same text for different prompts -- possible hardcoded stub."
    )


class _SilentNullResponseClient:
    """Returns None for every response field -- mimics a misbehaving SDK."""

    class _Msg:
        async def create(self, **kwargs: object) -> dict[str, object]:
            """Return a controlled payload."""
            return {"content": None, "usage": None, "model": None}

    messages: _Msg = _Msg()


async def test_empty_response_is_not_silently_ignored() -> None:
    """An empty server response must not produce a silent success.

    A real model completion should never return empty text with zero token
    counts, because that indicates an adapter-level bug or a silent failure
    in the provider SDK call.  The adapter should raise for an empty
    completion so the router can surface the error upstream.
    """
    provider = AnthropicModelProvider(
        api_key="test-key",
        client=cast(Any, _SilentNullResponseClient()),
    )
    prompt = PromptEnvelope(session_id=SessionId("s1"), messages=["Hello"])
    with pytest.raises(RuntimeError, match="no text completion"):
        await provider.complete(prompt)


async def test_fake_router_passes_non_existent_provider() -> None:
    """The router should refuse a provider that is not registered."""
    fake = FakeModelProvider()
    router = ModelRouter(
        providers={"real": fake},
        default="real",
        token_usage_repository=AsyncMock(),
    )
    prompt = PromptEnvelope(session_id=SessionId("s1"), messages=["Hello"])

    with pytest.raises(UnknownModelProviderError):
        await router.complete(prompt, provider="phantom", run_id="r1")


async def test_runtime_checkable_protocol_accepts_duck_types() -> None:
    """@runtime_checkable allows any class with a matching method signature
    to pass isinstance(provider, ModelProvider) -- even a bogus class with
    incorrect logic.

    This is a FEATURE of Python's structural typing, not a bug, but it means
    the "isinstance guard" in ModelRouter.__init__ does NOT catch classes
    that pass the isinstance() check but have incorrect logic.

    The test demonstrates that duck typing beats structural protection.
    """

    class _FakeProviderWithWrongLogic:
        """Deliberately wrong: returns the same text for every prompt."""

        async def complete(
            self, prompt: PromptEnvelope, *, tools: tuple[()] = (), stream: bool = False
        ) -> ModelCompletion:  # noqa: B027
            return ModelCompletion(
                session_id=prompt.session_id,
                text="always the same",  # BUG: ignores prompt
                model="fake",
                provider="duck-type",
                recorded_at=datetime.now(UTC),
                prompt_tokens=0,
                completion_tokens=1,
                total_tokens=1,
            )

    # This PASSES because Python duck typing checks signatures, not bodies
    fake = _FakeProviderWithWrongLogic()
    assert isinstance(fake, ModelProvider)

    # The router accepts it without complaint
    router = ModelRouter(
        providers={"wrong": fake},
        default="wrong",
        token_usage_repository=AsyncMock(),
    )

    # Different prompts produce the same output
    p1 = PromptEnvelope(session_id=SessionId("s1"), messages=["hello"])
    p2 = PromptEnvelope(session_id=SessionId("s2"), messages=["goodbye"])

    r1 = await router.complete(p1, run_id="r1")
    r2 = await router.complete(p2, run_id="r2")

    assert r1.text == r2.text == "always the same", (
        "Should have been 'always the same' (the bug). "
        "This test demonstrates that @runtime_checkable on a Protocol does NOT "
        "validate implementation correctness at instantiation time -- only "
        "method signature."
    )
