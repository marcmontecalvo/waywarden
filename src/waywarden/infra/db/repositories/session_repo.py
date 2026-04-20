"""SessionRepository implementation."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from waywarden.domain.session import Session
from waywarden.infra.db.models.session import sessions


class SessionRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, id: str) -> Session | None:
        stmt = sessions.select().where(sessions.c.id == id)
        result = await self._session.execute(stmt)
        row = result.fetchone()
        if row is None:
            return None
        return Session(
            id=row.id,
            instance_id=row.instance_id,
            profile=row.profile,
            created_at=_parse_ts(row.created_at) or datetime.now(UTC),
            closed_at=_parse_ts(row.closed_at) if row.closed_at else None,
        )

    async def save(self, session: Session) -> Session:
        stmt = sessions.insert().values(
            id=session.id,
            instance_id=session.instance_id,
            profile=session.profile,
            created_at=session.created_at,
            closed_at=session.closed_at if session.closed_at else None,
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return session


def _parse_ts(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    return datetime.fromisoformat(value)
