"""Unit tests for TokenUsage domain model."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from waywarden.domain.token_usage import (
    TokenUsage,
    TokenUsageModelRollup,
    TokenUsageSummary,
    summary_artifact_ref,
)


def _make_usage(
    run_id: str = "run_001",
    seq: int = 1,
    provider: str = "openai",
    model: str = "gpt-4",
    prompt_tokens: int = 100,
    completion_tokens: int = 50,
    call_ref: str | None = None,
) -> TokenUsage:
    return TokenUsage(
        id=str(uuid4()),
        run_id=run_id,
        seq=seq,
        provider=provider,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        recorded_at=datetime.now(UTC),
        call_ref=call_ref,
    )


class TestTokenUsageTotalTokensInvariant:
    """Acceptance criterion: total_tokens == prompt + completion enforced at construction."""

    def test_total_tokens_invariant(self) -> None:
        """Mismatched total_tokens raises ValueError."""
        with pytest.raises(ValueError, match="total_tokens.*must equal"):
            TokenUsage(
                id=str(uuid4()),
                run_id="run_001",
                seq=1,
                provider="openai",
                model="gpt-4",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=99,
                recorded_at=datetime.now(UTC),
            )

    def test_zero_tokens_are_valid(self) -> None:
        """Zero tokens pass validation."""
        u = _make_usage(prompt_tokens=0, completion_tokens=0)
        assert u.total_tokens == 0

    def test_negative_tokens_rejected(self) -> None:
        """Negative token counts raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            TokenUsage(
                id=str(uuid4()),
                run_id="run_001",
                seq=1,
                provider="openai",
                model="gpt-4",
                prompt_tokens=-1,
                completion_tokens=0,
                total_tokens=0,
                recorded_at=datetime.now(UTC),
            )

    def test_seq_must_be_positive(self) -> None:
        """seq < 1 raises ValueError."""
        with pytest.raises(ValueError, match="seq must be >= 1"):
            _make_usage(seq=0)

    def test_provider_must_be_non_empty(self) -> None:
        """Empty provider raises ValueError."""
        with pytest.raises(ValueError, match="provider"):
            TokenUsage(
                id=str(uuid4()),
                run_id="run_001",
                seq=1,
                provider="",
                model="gpt-4",
                prompt_tokens=1,
                completion_tokens=1,
                total_tokens=2,
                recorded_at=datetime.now(UTC),
            )

    def test_recorded_at_must_be_aware(self) -> None:
        """Naive datetime raises ValueError."""
        with pytest.raises(ValueError, match="timezone-aware"):
            TokenUsage(
                id=str(uuid4()),
                run_id="run_001",
                seq=1,
                provider="openai",
                model="gpt-4",
                prompt_tokens=1,
                completion_tokens=1,
                total_tokens=2,
                recorded_at=datetime(2025, 1, 1, 12, 0, 0),
            )


class TestSummaryArtifactRef:
    def test_format(self) -> None:
        ref = summary_artifact_ref("run_001")
        assert ref == "artifact://runs/run_001/usage-summary"

    def test_different_run_ids(self) -> None:
        assert summary_artifact_ref("abc") == "artifact://runs/abc/usage-summary"


class TestTokenUsageModelRollup:
    def test_frozen(self) -> None:
        rollup = TokenUsageModelRollup(
            model="gpt-4",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            call_count=1,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            rollup.prompt_tokens = 200


class TestTokenUsageSummary:
    def test_frozen(self) -> None:
        summary = TokenUsageSummary(
            run_id="run_001",
            total_prompt=100,
            total_completion=50,
            total_total=150,
            by_model={},
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            summary.run_id = "other"
