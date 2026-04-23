"""Integration tests for MessageRepository."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from waywarden.domain.ids import MessageId, SessionId
from waywarden.domain.message import Message
from waywarden.infra.db.repositories.message_repo import MessageRepositoryImpl


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """CREATE TABLE messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    metadata JSON
                )"""
            )
        )

    async with factory() as s:
        yield s

    await engine.dispose()


async def test_metadata_jsonb_roundtrip(session: AsyncSession) -> None:
    """Metadata survives save+reload as dict, not double-encoded string."""
    now = datetime.now(UTC)
    msg = Message(
        id=MessageId("msg_001"),
        session_id=SessionId("session_001"),
        role="user",
        content="Hello",
        created_at=now,
        metadata={"key": "value", "model": "gpt-4"},
    )
    repo = MessageRepositoryImpl(session)

    await repo.save(msg)
    loaded = await repo.get("msg_001")
    assert loaded is not None
    assert dict(loaded.metadata) == {"key": "value", "model": "gpt-4"}


async def test_list_by_session_returns_metadata(session: AsyncSession) -> None:
    """list_by_session returns messages with correct metadata."""
    now = datetime.now(UTC)
    msg = Message(
        id=MessageId("msg_002"),
        session_id=SessionId("session_002"),
        role="assistant",
        content="Hi there",
        created_at=now,
        metadata={"provider": "openai"},
    )
    repo = MessageRepositoryImpl(session)

    await repo.save(msg)
    msgs = await repo.list_by_session("session_002")
    assert len(msgs) == 1
    assert msgs[0].metadata == {"provider": "openai"}


async def test_get_nonexistent_returns_none(session: AsyncSession) -> None:
    """get() returns None for a message_id that was never saved."""
    repo = MessageRepositoryImpl(session)
    loaded = await repo.get("nonexistent")
    assert loaded is None


async def test_list_by_session_with_limit(session: AsyncSession) -> None:
    """list_by_session(limit=N) returns at most N messages."""
    repo = MessageRepositoryImpl(session)
    for i in range(5):
        now = datetime.now(UTC)
        msg = Message(
            id=MessageId(f"msg_limit_{i}"),
            session_id=SessionId("session_limit"),
            role="user",
            content=f"Message {i}",
            created_at=now,
            metadata={},
        )
        await repo.save(msg)

    limited = await repo.list_by_session("session_limit", limit=3)
    assert len(limited) == 3


async def test_list_by_session_empty_returns_empty_list(session: AsyncSession) -> None:
    """list_by_session for a session with no messages returns empty list."""
    repo = MessageRepositoryImpl(session)
    msgs = await repo.list_by_session("nonexistent_session")
    assert msgs == []
