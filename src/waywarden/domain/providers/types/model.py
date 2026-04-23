"""Value types for the model provider protocol."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from waywarden.domain.ids import SessionId


@dataclass(frozen=True, slots=True)
class PromptEnvelope:
    """A provider-neutral prompt sent to a model."""

    session_id: SessionId
    messages: list[str]
    tools: list[str] | None = None
    system_prompt: str | None = None

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id must not be empty")
        if not self.messages:
            raise ValueError("messages must not be empty")
        for m in self.messages:
            if not isinstance(m, str):
                raise TypeError("each message must be a string")


@dataclass(frozen=True, slots=True)
class ModelCompletion:
    """Response from a model completion call."""

    session_id: SessionId
    text: str
    model: str
    provider: str
    recorded_at: datetime
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id must not be empty")
        if not isinstance(self.text, str):
            raise TypeError("text must be a string")
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("model must be a non-empty string")
        if not isinstance(self.provider, str) or not self.provider.strip():
            raise ValueError("provider must be a non-empty string")
        if self.prompt_tokens < 0 or self.completion_tokens < 0:
            raise ValueError("token counts must be non-negative")
        if self.total_tokens != self.prompt_tokens + self.completion_tokens:
            raise ValueError("total_tokens must equal prompt_tokens + completion_tokens")
        if not isinstance(self.recorded_at, datetime):
            raise TypeError("recorded_at must be a datetime")
        if self.recorded_at.tzinfo is None or self.recorded_at.utcoffset() is None:
            raise ValueError("recorded_at must be timezone-aware")
        object.__setattr__(self, "recorded_at", self.recorded_at.astimezone(UTC))
