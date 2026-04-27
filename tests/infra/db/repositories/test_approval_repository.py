"""Integration tests for ApprovalRepository."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Literal

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from waywarden.domain.approval import Approval
from waywarden.domain.ids import ApprovalId, RunId
from waywarden.infra.db.repositories.approval_repo import ApprovalRepositoryImpl


def _make_approval(
    approval_id: str = "appr_001",
    run_id: str = "run_001",
    state: Literal["pending", "granted", "denied", "timeout"] = "pending",
    decided_at: datetime | None = None,
    decided_by: str | None = None,
    expires_at: datetime | None = None,
) -> Approval:
    now = datetime.now(UTC)
    return Approval(
        id=ApprovalId(approval_id),
        run_id=RunId(run_id),
        approval_kind="shell",
        requested_capability="execute",
        summary="Approve shell execution",
        state=state,
        requested_at=now,
        decided_at=decided_at,
        decided_by=decided_by,
        expires_at=expires_at,
    )


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """CREATE TABLE approvals (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    approval_kind TEXT NOT NULL,
                    requested_capability TEXT,
                    summary TEXT NOT NULL,
                    state TEXT NOT NULL,
                    requested_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    decided_at TIMESTAMP WITH TIME ZONE,
                    decided_by TEXT,
                    expires_at TIMESTAMP WITH TIME ZONE
                )"""
            )
        )

    async with factory() as s:
        yield s

    await engine.dispose()


async def test_save_and_get_roundtrip(session: AsyncSession) -> None:
    """save + get round-trips an Approval with all fields intact."""
    appr = _make_approval(approval_id="appr_rt")
    repo = ApprovalRepositoryImpl(session)

    saved = await repo.save(appr)
    assert saved.id == appr.id

    loaded = await repo.get("appr_rt")
    assert loaded is not None
    assert loaded.id == appr.id
    assert loaded.run_id == appr.run_id
    assert loaded.approval_kind == appr.approval_kind
    assert loaded.summary == appr.summary
    assert loaded.state == appr.state


async def test_get_nonexistent_returns_none(session: AsyncSession) -> None:
    """get() returns None for an approval_id that was never saved."""
    repo = ApprovalRepositoryImpl(session)
    loaded = await repo.get("nonexistent")
    assert loaded is None


async def test_list_by_run_returns_multiple_approvals(session: AsyncSession) -> None:
    """list_by_run returns all approvals for a given run_id."""
    appr1 = _make_approval(approval_id="appr_list_1", run_id="run_list")
    appr2 = _make_approval(approval_id="appr_list_2", run_id="run_list")
    appr3 = _make_approval(approval_id="appr_other", run_id="run_other")
    repo = ApprovalRepositoryImpl(session)

    await repo.save(appr1)
    await repo.save(appr2)
    await repo.save(appr3)

    results = await repo.list_by_run("run_list")
    assert len(results) == 2
    ids = {r.id for r in results}
    assert ids == {appr1.id, appr2.id}


async def test_granted_approval_with_decided_at(session: AsyncSession) -> None:
    """A granted approval preserves decided_at and decided_by through roundtrip."""
    requested = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    decided = datetime(2025, 1, 1, 12, 5, 0, tzinfo=UTC)
    appr = Approval(
        id=ApprovalId("appr_granted"),
        run_id=RunId("run_granted"),
        approval_kind="shell",
        requested_capability="execute",
        summary="Approve shell execution",
        state="granted",
        requested_at=requested,
        decided_at=decided,
        decided_by="user_1",
        expires_at=None,
    )
    repo = ApprovalRepositoryImpl(session)

    await repo.save(appr)
    loaded = await repo.get("appr_granted")
    assert loaded is not None
    assert loaded.state == "granted"
    assert loaded.decided_at is not None
    assert loaded.decided_by == "user_1"


async def test_save_returns_same_instance(session: AsyncSession) -> None:
    """save() returns the same instance for frozen dataclass semantics."""
    appr = _make_approval(approval_id="appr_return")
    repo = ApprovalRepositoryImpl(session)

    result = await repo.save(appr)
    assert result is appr


async def test_save_updates_existing_approval(session: AsyncSession) -> None:
    """save() overwrites an approval row when the engine resolves it."""
    repo = ApprovalRepositoryImpl(session)
    original = _make_approval(approval_id="appr_update", state="pending")
    decided_at = datetime.now(UTC)
    updated = Approval(
        id=original.id,
        run_id=original.run_id,
        approval_kind=original.approval_kind,
        requested_capability=original.requested_capability,
        summary=original.summary,
        state="granted",
        requested_at=original.requested_at,
        decided_at=decided_at,
        decided_by="operator-1",
        expires_at=original.expires_at,
    )

    await repo.save(original)
    await repo.save(updated)

    loaded = await repo.get("appr_update")
    assert loaded is not None
    assert loaded.state == "granted"
    assert loaded.decided_at == decided_at
    assert loaded.decided_by == "operator-1"
