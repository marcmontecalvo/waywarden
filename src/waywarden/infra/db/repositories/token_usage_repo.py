"""TokenUsageRepository — async SQLAlchemy implementation.

Enforces per-run monotonic ``seq`` via ``MAX(seq)+1`` (with ``FOR UPDATE``
fallback for databases that support it).  No ``run.usage`` event is ever
emitted — usage records live outside the RT-002 event log per spec.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from waywarden.domain.token_usage import (
    TokenUsage,
    TokenUsageModelRollup,
    TokenUsageSummary,
)
from waywarden.infra.db.models.token_usage import token_usage


def _row_to_usage(row: Any) -> TokenUsage:
    """Convert a token_usage row to a domain instance."""
    recorded_at = row.recorded_at
    if isinstance(recorded_at, str):
        recorded_at = datetime.fromisoformat(recorded_at)
    return TokenUsage(
        id=row.id,
        run_id=row.run_id,
        seq=int(row.seq),
        provider=row.provider,
        model=row.model,
        prompt_tokens=int(row.prompt_tokens),
        completion_tokens=int(row.completion_tokens),
        total_tokens=int(row.total_tokens),
        recorded_at=recorded_at,
        call_ref=row.call_ref,
    )


def _usage_to_values(entry: TokenUsage) -> dict[str, object]:
    """Serialize a TokenUsage domain instance to a dict for insertion."""
    return {
        "id": entry.id,
        "run_id": entry.run_id,
        "seq": entry.seq,
        "provider": entry.provider,
        "model": entry.model,
        "prompt_tokens": entry.prompt_tokens,
        "completion_tokens": entry.completion_tokens,
        "total_tokens": entry.total_tokens,
        "recorded_at": entry.recorded_at.isoformat(),
        "call_ref": entry.call_ref,
    }


class TokenUsageRepositoryImpl:
    """Async SQLAlchemy implementation of TokenUsageRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, entry: TokenUsage) -> TokenUsage:
        """Append a token usage record with per-run monotonic seq enforcement."""
        run_id = entry.run_id

        # Compute next seq under row-level lock
        next_seq = await self._compute_next_seq(run_id)

        # Override seq with computed value (domain may have a placeholder)
        entry = TokenUsage(
            id=entry.id,
            run_id=entry.run_id,
            seq=next_seq,
            provider=entry.provider,
            model=entry.model,
            prompt_tokens=entry.prompt_tokens,
            completion_tokens=entry.completion_tokens,
            total_tokens=entry.total_tokens,
            recorded_at=entry.recorded_at,
            call_ref=entry.call_ref,
        )

        values = _usage_to_values(entry)
        stmt = token_usage.insert().values(**values)
        await self._session.execute(stmt)
        await self._session.flush()
        return entry

    async def list(self, run_id: str) -> list[TokenUsage]:
        """Return all usage records for *run_id*, ordered by seq ascending."""
        stmt = (
            token_usage.select()
            .where(token_usage.c.run_id == run_id)
            .order_by(token_usage.c.seq)
        )
        result = await self._session.execute(stmt)
        rows = result.fetchall()
        return [_row_to_usage(row) for row in rows]

    async def summarize(self, run_id: str) -> TokenUsageSummary:
        """Aggregate token usage for *run_id* into a summary with per-model rollups."""
        stmt = (
            token_usage.select()
            .where(token_usage.c.run_id == run_id)
            .order_by(token_usage.c.seq)
        )
        result = await self._session.execute(stmt)
        rows = result.fetchall()

        total_prompt = 0
        total_completion = 0
        total_total = 0
        by_model: dict[str, dict[str, int]] = {}

        for row in rows:
            pt = int(row.prompt_tokens)
            ct = int(row.completion_tokens)
            tt = int(row.total_tokens)
            model = row.model

            total_prompt += pt
            total_completion += ct
            total_total += tt

            if model not in by_model:
                by_model[model] = {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "call_count": 0,
                }
            by_model[model]["prompt_tokens"] += pt
            by_model[model]["completion_tokens"] += ct
            by_model[model]["total_tokens"] += tt
            by_model[model]["call_count"] += 1

        rollups: dict[str, TokenUsageModelRollup] = {}
        for model, mdata in by_model.items():
            rollups[model] = TokenUsageModelRollup(
                model=model,
                prompt_tokens=mdata["prompt_tokens"],
                completion_tokens=mdata["completion_tokens"],
                total_tokens=mdata["total_tokens"],
                call_count=mdata["call_count"],
            )

        return TokenUsageSummary(
            run_id=run_id,
            total_prompt=total_prompt,
            total_completion=total_completion,
            total_total=total_total,
            by_model=rollups,
        )

    # -- private helpers -----------------------------------------------------

    async def _compute_next_seq(self, run_id: str) -> int:
        """Compute next seq under ``FOR UPDATE`` lock.

        Uses a subquery to lock rows while computing MAX(seq), avoiding
        Postgres's restriction on FOR UPDATE with aggregate functions.
        Falls back to a non-locking query on databases that don't support
        ``FOR UPDATE`` (e.g. SQLite in tests).
        """
        try:
            stmt = text(
                "SELECT COALESCE(MAX(seq), 0) + 1 "
                "FROM (SELECT seq FROM token_usage "
                "WHERE run_id = :run_id FOR UPDATE) sub"
            )
            result = await self._session.execute(
                stmt, {"run_id": run_id}
            )
        except Exception:
            stmt = text(
                "SELECT COALESCE(MAX(seq), 0) + 1 "
                "FROM token_usage "
                "WHERE run_id = :run_id"
            )
            result = await self._session.execute(
                stmt, {"run_id": run_id}
            )
        next_seq = result.scalar_one()
        return int(next_seq)
