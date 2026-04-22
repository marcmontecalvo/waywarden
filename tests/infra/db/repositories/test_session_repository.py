"""Integration tests for SessionRepository."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from waywarden.domain.ids import InstanceId, SessionId
from waywarden.domain.session import Session
from waywarden.infra.db.repositories.session_repo import SessionRepositoryImpl


def _make_session(
    session_id: str = "sess_001",
    instance_id: str = "inst_001",
    profile: str = "default",
    closed: bool = False,
) -> Session:
    now = datetime.now(UTC)
    return Session(
        id=SessionId(session_id),
        instance_id=InstanceId(instance_id),
        profile=profile,
        created_at=now,
        closed_at=now if closed else None,
    )


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """CREATE TABLE sessions (
                    id TEXT PRIMARY KEY,
                    instance_id TEXT NOT NULL,
                    profile TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    closed_at TIMESTAMP WITH TIME ZONE
                )"""
            )
        )

    async with factory() as s:
        yield s

    await engine.dispose()


async def test_save_and_get_roundtrip(session: AsyncSession) -> None:
    """save + get round-trips a Session with all fields intact."""
    now = datetime.now(UTC)
    sess = Session(
        id=SessionId("sess_rt"),
        instance_id=InstanceId("inst_rt"),
        profile="rt-profile",
        created_at=now,
        closed_at=None,
    )
    repo = SessionRepositoryImpl(session)

    saved = await repo.save(sess)
    assert saved.id == sess.id

    loaded = await repo.get("sess_rt")
    assert loaded is not None
    assert loaded.id == sess.id
    assert loaded.instance_id == sess.instance_id
    assert loaded.profile == sess.profile
    assert loaded.closed_at is None


async def test_get_nonexistent_returns_none(session: AsyncSession) -> None:
    """get() returns None for a session_id that was never saved."""
    repo = SessionRepositoryImpl(session)
    loaded = await repo.get("nonexistent")
    assert loaded is None


async def test_closed_session_roundtrip(session: AsyncSession) -> None:
    """A closed session preserves closed_at through roundtrip."""
    sess = _make_session(session_id="sess_closed", closed=True)
    repo = SessionRepositoryImpl(session)

    await repo.save(sess)
    loaded = await repo.get("sess_closed")
    assert loaded is not None
    assert loaded.closed_at is not None
    assert loaded.closed_at.tzinfo is not None
