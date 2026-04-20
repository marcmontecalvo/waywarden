"""CheckpointRepository implementation."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from waywarden.domain.checkpoint import Checkpoint
from waywarden.infra.db.models.checkpoint import checkpoints


class CheckpointRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, id: str) -> Checkpoint | None:
        stmt = checkpoints.select().where(checkpoints.c.id == id)
        result = await self._session.execute(stmt)
        row = result.fetchone()
        if row is None:
            return None
        return Checkpoint(
            id=row.id,
            run_id=row.run_id,
            kind=row.kind,
            created_at=_parse_ts(row.created_at),
            label=row.label,
        )

    async def save(self, checkpoint: Checkpoint) -> Checkpoint:
        stmt = checkpoints.insert().values(
            id=checkpoint.id,
            run_id=checkpoint.run_id,
            kind=checkpoint.kind,
            created_at=checkpoint.created_at,
            label=checkpoint.label,
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return checkpoint

    async def list_by_run(self, run_id: str) -> list[Checkpoint]:
        stmt = checkpoints.select().where(checkpoints.c.run_id == run_id)
        result = await self._session.execute(stmt)
        rows = result.fetchall()
        return [
            Checkpoint(
                id=r.id,
                run_id=r.run_id,
                kind=r.kind,
                created_at=_parse_ts(r.created_at),
                label=r.label,
            )
            for r in rows
        ]


def _parse_ts(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    return datetime.fromisoformat(value)
