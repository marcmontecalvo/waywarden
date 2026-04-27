"""TaskRepository implementation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from waywarden.domain.task import Task
from waywarden.infra.db.models.task import tasks


class TaskRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, id: str) -> Task | None:
        stmt = tasks.select().where(tasks.c.id == id)
        result = await self._session.execute(stmt)
        row = result.fetchone()
        if row is None:
            return None
        return Task(
            id=row.id,
            session_id=row.session_id,
            title=row.title,
            objective=row.objective,
            state=row.state,
            created_at=_parse_ts(row.created_at),
            updated_at=_parse_ts(row.updated_at),
        )

    async def save(self, task: Task) -> Task:
        values = dict(
            id=task.id,
            session_id=task.session_id,
            title=task.title,
            objective=task.objective,
            state=task.state,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
        existing = await self.get(str(task.id))
        if existing is None:
            stmt: Any = tasks.insert().values(**values)
        else:
            stmt = tasks.update().where(tasks.c.id == task.id).values(**values)
        await self._session.execute(stmt)
        await self._session.flush()
        return task


def _parse_ts(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    return datetime.fromisoformat(value)
