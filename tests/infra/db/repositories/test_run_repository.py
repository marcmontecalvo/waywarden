"""Integration tests for RunRepository."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from waywarden.domain.ids import InstanceId, RunId, TaskId
from waywarden.domain.run import Run
from waywarden.infra.db.repositories.run_repo import RunRepositoryImpl


def _make_run(run_id: str = "run_001") -> Run:
    now = datetime.now(UTC)
    return Run(
        id=RunId(run_id),
        instance_id=InstanceId("inst_001"),
        task_id=TaskId("task_001"),
        profile="test",
        policy_preset="ask",
        manifest_ref="manifest://runs/run_001/v1",
        entrypoint="cli",
        state="created",
        created_at=now,
        updated_at=now,
        terminal_seq=None,
    )


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """CREATE TABLE runs (
                    id TEXT PRIMARY KEY,
                    instance_id TEXT NOT NULL,
                    task_id TEXT,
                    profile TEXT NOT NULL,
                    policy_preset TEXT NOT NULL,
                    manifest_ref TEXT NOT NULL,
                    entrypoint TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'created',
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    terminal_seq TEXT,
                    CHECK (policy_preset IN ('yolo', 'ask', 'allowlist', 'custom')),
                    CHECK (state IN ('created', 'planning', 'executing',
                        'waiting_approval', 'completed', 'failed', 'cancelled'))
                )"""
            )
        )

    async with factory() as s:
        yield s

    await engine.dispose()


async def test_load_after_insert_roundtrips(session: AsyncSession) -> None:
    """create + get round-trips a Run with all fields intact."""
    run = _make_run()
    repo = RunRepositoryImpl(session)

    created = await repo.create(run)
    assert created.id == run.id

    loaded = await repo.get(str(run.id))
    assert loaded is not None
    assert loaded.id == run.id
    assert loaded.state == run.state
    assert loaded.profile == run.profile
    assert loaded.policy_preset == run.policy_preset
    assert loaded.manifest_ref == run.manifest_ref
    assert loaded.entrypoint == run.entrypoint


async def test_terminal_seq_type_roundtrip(session: AsyncSession) -> None:
    """update_state sets terminal_seq as int; get() reloads as int."""
    run = _make_run("run_seq_test")
    repo = RunRepositoryImpl(session)
    await repo.create(run)

    # Update state with a terminal_seq value
    updated = await repo.update_state(str(run.id), "completed", 9)
    assert updated.terminal_seq == 9
    assert isinstance(updated.terminal_seq, int)

    # Reload via get() — must return int, not str
    loaded = await repo.get(str(run.id))
    assert loaded is not None
    assert loaded.terminal_seq == 9
    assert isinstance(loaded.terminal_seq, int)


async def test_get_nonexistent_returns_none(session: AsyncSession) -> None:
    """get() returns None for a run_id that was never created."""
    repo = RunRepositoryImpl(session)
    loaded = await repo.get("nonexistent")
    assert loaded is None


async def test_load_latest_state_matches_get(session: AsyncSession) -> None:
    """load_latest_state() returns the same result as get()."""
    run = _make_run("run_latest")
    repo = RunRepositoryImpl(session)
    await repo.create(run)

    latest = await repo.load_latest_state(str(run.id))
    direct = await repo.get(str(run.id))
    assert latest is not None
    assert latest.id == direct.id
    assert latest.state == direct.state
