"""Integration tests for RunEventRepository."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from waywarden.domain.ids import InstanceId, RunEventId, RunId, TaskId
from waywarden.domain.repositories import TerminalRunStateError
from waywarden.domain.run import Run
from waywarden.domain.run_event import Actor, Causation, RunEvent
from waywarden.domain.run_event_types import RunEventType
from waywarden.infra.db.models.run import runs
from waywarden.infra.db.repositories.run_event_repo import RunEventRepositoryImpl


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


def _make_event(
    run_id: str = "run_001",
    seq: int = 1,
    event_type: RunEventType = "run.created",
) -> RunEvent:
    return RunEvent(
        id=RunEventId(f"evt_{uuid4().hex[:12]}"),
        run_id=RunId(run_id),
        seq=seq,
        type=event_type,
        payload={
            "instance_id": "inst_001",
            "profile": "test",
            "policy_preset": "ask",
            "manifest_ref": "m",
            "entrypoint": "cli",
        },
        timestamp=datetime.now(UTC),
        causation=Causation(
            event_id=f"ca_{uuid4().hex[:8]}",
            action=None,
            request_id=None,
        ),
        actor=Actor(kind="system", id=None, display=None),
    )


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Create only the tables we need
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
        await conn.execute(
            text(
                """CREATE TABLE run_events (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    payload TEXT,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    causation TEXT,
                    actor TEXT,
                    UNIQUE(run_id, seq),
                    CHECK (seq >= 1),
                    CHECK (type IN ('run.created', 'run.plan_ready',
                        'run.execution_started', 'run.progress',
                        'run.approval_waiting', 'run.resumed',
                        'run.artifact_created', 'run.completed',
                        'run.failed', 'run.cancelled'))
                )"""
            )
        )

    async with factory() as s:
        yield s

    await engine.dispose()


@pytest_asyncio.fixture
async def run_and_repo(session: AsyncSession) -> tuple[Run, RunEventRepositoryImpl]:
    """Insert a run and return (run, repo)."""
    run = _make_run()
    stmt = runs.insert().values(
        id=run.id,
        instance_id=run.instance_id,
        task_id=run.task_id,
        profile=run.profile,
        policy_preset=run.policy_preset,
        manifest_ref=run.manifest_ref,
        entrypoint=run.entrypoint,
        state=run.state,
        created_at=run.created_at,
        updated_at=run.updated_at,
        terminal_seq=run.terminal_seq,
    )
    await session.execute(stmt)
    await session.flush()
    repo = RunEventRepositoryImpl(session)
    return (run, repo)


async def test_append_assigns_monotonic_seq(
    run_and_repo: tuple[Run, RunEventRepositoryImpl],
) -> None:
    """append() assigns strictly increasing seq starting at 1."""
    run, repo = run_and_repo
    run_id = str(run.id)
    for i in range(5):
        evt = _make_event(run_id=run_id, seq=i + 1)
        result = await repo.append(evt)
        assert result.seq == i + 1


async def test_concurrent_appends_strictly_increase_seq(
    run_and_repo: tuple[Run, RunEventRepositoryImpl],
) -> None:
    """20 sequential appends produce no duplicate seq (SQLite serializes)."""
    run, repo = run_and_repo
    run_id = str(run.id)
    seqs: list[int] = []
    for _ in range(20):
        result = await repo.append(_make_event(run_id=run_id))
        seqs.append(result.seq)
    assert len(seqs) == 20
    assert len(set(seqs)) == 20
    assert seqs == sorted(seqs)


async def test_append_after_terminal_rejected(session: AsyncSession) -> None:
    """Appending to a completed run raises TerminalRunStateError."""
    from waywarden.infra.db.repositories.run_event_repo import (
        RunEventRepositoryImpl,
    )

    run = _make_run("run_terminal")
    stmt = runs.insert().values(
        id=run.id,
        instance_id=run.instance_id,
        task_id=run.task_id,
        profile=run.profile,
        policy_preset=run.policy_preset,
        manifest_ref=run.manifest_ref,
        entrypoint=run.entrypoint,
        state=run.state,
        created_at=run.created_at,
        updated_at=run.updated_at,
        terminal_seq=run.terminal_seq,
    )
    await session.execute(stmt)
    await session.flush()

    repo = RunEventRepositoryImpl(session)
    run_id = str(run.id)

    # Mark run as completed
    await session.execute(
        text("UPDATE runs SET state = 'completed', terminal_seq = 1 WHERE id = :rid").bindparams(
            rid=run_id
        )
    )
    await session.flush()

    # Next append must fail
    with pytest.raises(TerminalRunStateError):
        await repo.append(_make_event(run_id=run_id, seq=1))


async def test_list_since_seq_returns_tail(
    run_and_repo: tuple[Run, RunEventRepositoryImpl],
) -> None:
    """list(since_seq=N) returns events with seq > N, ordered ascending."""
    run, repo = run_and_repo
    run_id = str(run.id)
    for i in range(5):
        await repo.append(_make_event(run_id=run_id, seq=i + 1))

    tail = await repo.list(run_id, since_seq=2)
    assert len(tail) == 3
    assert [e.seq for e in tail] == [3, 4, 5]


async def test_latest_seq_returns_zero_for_empty_run(session: AsyncSession) -> None:
    """latest_seq returns 0 when no events exist for a run."""
    run = _make_run("run_empty")
    stmt = runs.insert().values(
        id=run.id,
        instance_id=run.instance_id,
        task_id=run.task_id,
        profile=run.profile,
        policy_preset=run.policy_preset,
        manifest_ref=run.manifest_ref,
        entrypoint=run.entrypoint,
        state=run.state,
        created_at=run.created_at,
        updated_at=run.updated_at,
        terminal_seq=run.terminal_seq,
    )
    await session.execute(stmt)
    await session.flush()

    repo = RunEventRepositoryImpl(session)
    assert await repo.latest_seq(str(run.id)) == 0


async def test_payload_identity_roundtrip(run_and_repo: tuple[Run, RunEventRepositoryImpl]) -> None:
    """Payload survives JSON roundtrip without _assigned_seq injection."""
    run, repo = run_and_repo
    run_id = str(run.id)

    original_payload = {
        "instance_id": "inst_001",
        "profile": "test",
        "policy_preset": "ask",
        "manifest_ref": "m",
        "entrypoint": "cli",
    }
    evt = RunEvent(
        id=RunEventId(f"evt_{uuid4().hex[:12]}"),
        run_id=RunId(run_id),
        seq=1,
        type="run.created",
        payload=original_payload,
        timestamp=datetime.now(UTC),
        causation=Causation(
            event_id=f"ca_{uuid4().hex[:8]}",
            action=None,
            request_id=None,
        ),
        actor=Actor(kind="system", id=None, display=None),
    )
    await repo.append(evt)

    events = await repo.list(run_id)
    assert len(events) == 1
    loaded_payload = dict(events[0].payload)
    assert "_assigned_seq" not in loaded_payload
    assert loaded_payload == original_payload
