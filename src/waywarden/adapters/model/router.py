"""Runtime model provider router with token usage accounting."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import uuid4

from waywarden.domain.providers import ModelProvider
from waywarden.domain.providers.types.model import ModelCompletion, PromptEnvelope
from waywarden.domain.providers.types.tool import ToolDecl
from waywarden.domain.repositories import TokenUsageRepository
from waywarden.domain.token_usage import TokenUsage


class UnknownModelProviderError(ValueError):
    """Raised when a requested model provider is not registered."""


class MissingRunIdError(ValueError):
    """Raised when token accounting cannot be tied to a run."""


class ModelRouter:
    """Route model completions to configured providers and record usage."""

    def __init__(
        self,
        *,
        providers: Mapping[str, ModelProvider],
        default: str,
        token_usage_repository: TokenUsageRepository,
    ) -> None:
        if not providers:
            raise ValueError("providers must not be empty")
        if default not in providers:
            raise UnknownModelProviderError(f"default provider {default!r} is not registered")
        for name, provider in providers.items():
            if not isinstance(provider, ModelProvider):
                raise TypeError(f"provider {name!r} does not implement ModelProvider")

        self._providers = dict(providers)
        self._default = default
        self._token_usage_repository = token_usage_repository

    async def complete(
        self,
        prompt: PromptEnvelope,
        *,
        provider: str | None = None,
        tools: Sequence[ToolDecl] = (),
        stream: bool = False,
        run_id: str | None = None,
        call_ref: str | None = None,
    ) -> ModelCompletion:
        selected_name = provider or self._default
        selected_provider = self._provider(selected_name)
        completion = await selected_provider.complete(prompt, tools=tools, stream=stream)
        await self._record_usage(completion, run_id=run_id, call_ref=call_ref)
        return completion

    def _provider(self, name: str) -> ModelProvider:
        try:
            return self._providers[name]
        except KeyError as exc:
            raise UnknownModelProviderError(f"model provider {name!r} is not registered") from exc

    async def _record_usage(
        self,
        completion: ModelCompletion,
        *,
        run_id: str | None,
        call_ref: str | None,
    ) -> None:
        if not run_id:
            raise MissingRunIdError("run_id is required for token usage accounting")
        entry = TokenUsage(
            id=f"usage_{uuid4().hex}",
            run_id=run_id,
            seq=1,
            provider=completion.provider,
            model=completion.model,
            prompt_tokens=completion.prompt_tokens,
            completion_tokens=completion.completion_tokens,
            total_tokens=completion.total_tokens,
            recorded_at=completion.recorded_at,
            call_ref=call_ref,
        )
        await self._token_usage_repository.append(entry)
