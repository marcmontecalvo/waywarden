"""Integration tests for CheckpointRepository."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from waywarden.domain.checkpoint import Checkpoint, CheckpointKind
from waywarden.domain.ids import CheckpointId, RunId
from waywarden.infra.db.repositories.checkpoint_repo import CheckpointRepositoryImpl


def _make_checkpoint(
    checkpoint_id: str = "ckp_001",
    run_id: str = "run_001",
    kind: CheckpointKind = "plan",
    label: str | None = None,
) -> Checkpoint:
    return Checkpoint(
        id=CheckpointId(checkpoint_id),
        run_id=RunId(run_id),
        kind=kind,
        created_at=datetime.now(UTC),
        label=label,
    )


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """CREATE TABLE checkpoints (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    label TEXT
                )"""
            )
        )

    async with factory() as s:
        yield s

    await engine.dispose()


async def test_save_and_get_roundtrip(session: AsyncSession) -> None:
    """save + get round-trips a Checkpoint with all fields intact."""
    ckp = _make_checkpoint(checkpoint_id="ckp_rt", kind="pre_approval", label="before-approve")
    repo = CheckpointRepositoryImpl(session)

    saved = await repo.save(ckp)
    assert saved.id == ckp.id

    loaded = await repo.get("ckp_rt")
    assert loaded is not None
    assert loaded.id == ckp.id
    assert loaded.run_id == ckp.run_id
    assert loaded.kind == ckp.kind
    assert loaded.label == "before-approve"


async def test_get_nonexistent_returns_none(session: AsyncSession) -> None:
    """get() returns None for a checkpoint_id that was never saved."""
    repo = CheckpointRepositoryImpl(session)
    loaded = await repo.get("nonexistent")
    assert loaded is None


async def test_list_by_run_returns_multiple_checkpoints(session: AsyncSession) -> None:
    """list_by_run returns all checkpoints for a given run_id."""
    ckp1 = _make_checkpoint(checkpoint_id="ckp_list_1", run_id="run_list", kind="plan")
    ckp2 = _make_checkpoint(checkpoint_id="ckp_list_2", run_id="run_list", kind="recovery")
    ckp3 = _make_checkpoint(checkpoint_id="ckp_other", run_id="run_other", kind="plan")
    repo = CheckpointRepositoryImpl(session)

    await repo.save(ckp1)
    await repo.save(ckp2)
    await repo.save(ckp3)

    results = await repo.list_by_run("run_list")
    assert len(results) == 2
    ids = {r.id for r in results}
    assert ids == {ckp1.id, ckp2.id}


async def test_checkpoint_with_none_label(session: AsyncSession) -> None:
    """A checkpoint with label=None survives roundtrip."""
    ckp = _make_checkpoint(checkpoint_id="ckp_null_label", label=None)
    repo = CheckpointRepositoryImpl(session)

    await repo.save(ckp)
    loaded = await repo.get("ckp_null_label")
    assert loaded is not None
    assert loaded.label is None
