"""Model provider protocol."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from waywarden.domain.providers.types.model import ModelCompletion, PromptEnvelope
from waywarden.domain.providers.types.tool import ToolDecl


@runtime_checkable
class ModelProvider(Protocol):
    """Protocol for model completion providers.

    All provider SDK types must stay out of this module.
    """

    async def complete(
        self,
        prompt: PromptEnvelope,
        *,
        tools: Sequence[ToolDecl] = (),
        stream: bool = False,
    ) -> ModelCompletion: ...
