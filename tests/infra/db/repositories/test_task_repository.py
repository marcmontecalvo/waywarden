"""Integration tests for TaskRepository."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from waywarden.domain.ids import SessionId, TaskId
from waywarden.domain.task import Task
from waywarden.infra.db.repositories.task_repo import TaskRepositoryImpl


def _make_task(
    task_id: str = "task_001",
    session_id: str = "sess_001",
    state: str = "draft",
) -> Task:
    now = datetime.now(UTC)
    return Task(
        id=TaskId(task_id),
        session_id=SessionId(session_id),
        title="Test task",
        objective="Complete the test",
        state=state,
        created_at=now,
        updated_at=now,
    )


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """CREATE TABLE tasks (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
                )"""
            )
        )

    async with factory() as s:
        yield s

    await engine.dispose()


async def test_save_and_get_roundtrip(session: AsyncSession) -> None:
    """save + get round-trips a Task with all fields intact."""
    task = _make_task(task_id="task_rt")
    repo = TaskRepositoryImpl(session)

    saved = await repo.save(task)
    assert saved.id == task.id

    loaded = await repo.get("task_rt")
    assert loaded is not None
    assert loaded.id == task.id
    assert loaded.session_id == task.session_id
    assert loaded.title == task.title
    assert loaded.objective == task.objective
    assert loaded.state == task.state


async def test_get_nonexistent_returns_none(session: AsyncSession) -> None:
    """get() returns None for a task_id that was never saved."""
    repo = TaskRepositoryImpl(session)
    loaded = await repo.get("nonexistent")
    assert loaded is None


async def test_state_roundtrip(session: AsyncSession) -> None:
    """Task state survives save+reload correctly."""
    task = _make_task(task_id="task_state", state="executing")
    repo = TaskRepositoryImpl(session)

    await repo.save(task)
    loaded = await repo.get("task_state")
    assert loaded is not None
    assert loaded.state == "executing"
