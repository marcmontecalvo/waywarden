"""TokenUsage domain model — per-call token accounting outside the RT-002 event log.

RT-002 §Token usage accounting:
- Usage records are persisted through a dedicated TokenUsageRepository.
- A run-scoped usage summary may be registered as a durable artifact via
  ``run.artifact_created`` with ``artifact_kind = usage-summary``.
- Implementations must NOT emit ``run.usage`` or similar non-catalog event types.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

TokenUsageId = str


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Immutable per-call token usage record."""

    id: TokenUsageId
    run_id: str
    seq: int
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    recorded_at: datetime
    call_ref: str | None = None

    def __post_init__(self) -> None:
        if self.prompt_tokens < 0 or self.completion_tokens < 0 or self.total_tokens < 0:
            raise ValueError("token counts must be non-negative")
        if self.total_tokens != self.prompt_tokens + self.completion_tokens:
            raise ValueError("total_tokens must equal prompt_tokens + completion_tokens")
        if self.seq < 1:
            raise ValueError("seq must be >= 1")
        if not isinstance(self.provider, str) or not self.provider.strip():
            raise ValueError("provider must be a non-empty string")
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("model must be a non-empty string")
        if not isinstance(self.recorded_at, datetime):
            raise TypeError("recorded_at must be a datetime")
        if self.recorded_at.tzinfo is None or self.recorded_at.utcoffset() is None:
            raise ValueError("recorded_at must be timezone-aware")
        object.__setattr__(self, "recorded_at", self.recorded_at.astimezone(UTC))


@dataclass(frozen=True, slots=True)
class TokenUsageModelRollup:
    """Rollup for a single model within a run."""

    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    call_count: int


@dataclass(frozen=True, slots=True)
class TokenUsageSummary:
    """Aggregated token usage for a run."""

    run_id: str
    total_prompt: int
    total_completion: int
    total_total: int
    by_model: Mapping[str, TokenUsageModelRollup]


def summary_artifact_ref(run_id: str) -> str:
    """Return the RT-002 artifact_ref for a run's usage summary.

    Format: ``artifact://runs/{run_id}/usage-summary``
    """
    return f"artifact://runs/{run_id}/usage-summary"
