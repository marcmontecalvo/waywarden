"""Integration tests for TokenUsageRepository."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from waywarden.domain.token_usage import (
    TokenUsage,
    TokenUsageModelRollup,
    summary_artifact_ref,
)
from waywarden.infra.db.repositories.token_usage_repo import (
    TokenUsageRepositoryImpl,
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


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """CREATE TABLE token_usage (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    recorded_at TEXT NOT NULL,
                    call_ref TEXT,
                    UNIQUE(run_id, seq),
                    CHECK (seq >= 1),
                    CHECK (total_tokens = prompt_tokens + completion_tokens),
                    CHECK (prompt_tokens >= 0 AND completion_tokens >= 0 AND total_tokens >= 0)
                )"""
            )
        )

    async with factory() as s:
        yield s

    await engine.dispose()


async def test_append_monotonic_seq(session: AsyncSession) -> None:
    """append() assigns strictly increasing seq starting at 1."""
    repo = TokenUsageRepositoryImpl(session)
    run_id = "run_mono"

    seqs: list[int] = []
    for i in range(10):
        entry = _make_usage(run_id=run_id, seq=i + 1)
        result = await repo.append(entry)
        seqs.append(result.seq)
        assert result.seq == i + 1

    assert len(seqs) == 10
    assert len(set(seqs)) == 10
    assert seqs == sorted(seqs)


async def test_list_returns_ordered_entries(session: AsyncSession) -> None:
    """list() returns entries ordered by seq ascending."""
    repo = TokenUsageRepositoryImpl(session)
    run_id = "run_list"

    for i in range(5):
        await repo.append(_make_usage(run_id=run_id, seq=i + 1))

    entries = await repo.list(run_id)
    assert len(entries) == 5
    assert [e.seq for e in entries] == [1, 2, 3, 4, 5]


async def test_summarize_by_model(session: AsyncSession) -> None:
    """summarize() aggregates totals and per-model rollups correctly."""
    repo = TokenUsageRepositoryImpl(session)
    run_id = "run_sum"

    await repo.append(
        _make_usage(
            run_id=run_id, seq=1, provider="openai",
            model="gpt-4", prompt_tokens=100, completion_tokens=50
        )
    )
    await repo.append(
        _make_usage(
            run_id=run_id, seq=2, provider="openai",
            model="gpt-4", prompt_tokens=200, completion_tokens=100
        )
    )
    await repo.append(
        _make_usage(
            run_id=run_id, seq=3, provider="openai",
            model="gpt-3.5", prompt_tokens=50, completion_tokens=25
        )
    )

    summary = await repo.summarize(run_id)

    assert summary.run_id == run_id
    assert summary.total_prompt == 350
    assert summary.total_completion == 175
    assert summary.total_total == 525

    assert len(summary.by_model) == 2

    gpt4 = summary.by_model["gpt-4"]
    assert isinstance(gpt4, TokenUsageModelRollup)
    assert gpt4.prompt_tokens == 300
    assert gpt4.completion_tokens == 150
    assert gpt4.total_tokens == 450
    assert gpt4.call_count == 2

    gpt35 = summary.by_model["gpt-3.5"]
    assert gpt35.prompt_tokens == 50
    assert gpt35.completion_tokens == 25
    assert gpt35.total_tokens == 75
    assert gpt35.call_count == 1


async def test_summarize_empty_run(session: AsyncSession) -> None:
    """summarize on a run with no entries returns zero totals."""
    repo = TokenUsageRepositoryImpl(session)
    summary = await repo.summarize("nonexistent")

    assert summary.total_prompt == 0
    assert summary.total_completion == 0
    assert summary.total_total == 0
    assert len(summary.by_model) == 0


async def test_summary_artifact_ref_format() -> None:
    """artifact_ref matches RT-002 format."""
    ref = summary_artifact_ref("run_001")
    assert ref == "artifact://runs/run_001/usage-summary"


async def test_no_run_usage_event_emitted() -> None:
    """Static grep: no code in src/ emits 'run.usage' event type.

    RT-002 rev-2 explicitly forbids this event type.
    """
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-c", r"""
import pathlib, sys

src = pathlib.Path("src")
hits = []
for f in src.rglob("*.py"):
    content = f.read_text()
    # Look for string literals containing 'run.usage'
    for line in content.splitlines():
        stripped = line.strip()
        if '"run.usage"' in stripped or "'run.usage'" in stripped:
            hits.append(f"{f}:{stripped}")

if hits:
    for h in hits:
        print(h)
    sys.exit(1)
sys.exit(0)
"""],
        cwd=".",
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Found 'run.usage' references in source:\n{result.stdout}"
    )
