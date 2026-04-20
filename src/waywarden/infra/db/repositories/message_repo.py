"""MessageRepository implementation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from waywarden.domain.message import Message
from waywarden.infra.db.models.message import messages


class MessageRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, id: str) -> Message | None:
        stmt = messages.select().where(messages.c.id == id)
        result = await self._session.execute(stmt)
        row = result.fetchone()
        if row is None:
            return None
        return Message(
            id=row.id,
            session_id=row.session_id,
            role=row.role,
            content=row.content,
            created_at=_parse_ts(row.created_at),
            metadata=_parse_metadata(row.metadata) if row.metadata else {},
        )

    async def save(self, message: Message) -> Message:
        import json

        stmt = messages.insert().values(
            id=message.id,
            session_id=message.session_id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
            metadata=json.dumps(dict(message.metadata)),
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return message

    async def list_by_session(
        self,
        session_id: str,
        *,
        limit: int | None = None,
    ) -> list[Message]:
        stmt = (
            messages.select()
            .where(messages.c.session_id == session_id)
            .order_by(messages.c.created_at)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        rows = result.fetchall()
        return [
            Message(
                id=r.id,
                session_id=r.session_id,
                role=r.role,
                content=r.content,
                created_at=_parse_ts(r.created_at),
                metadata=_parse_metadata(r.metadata) if r.metadata else {},
            )
            for r in rows
        ]


def _parse_ts(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    return datetime.fromisoformat(value)


def _parse_metadata(value: str | None) -> dict[str, str]:
    if value is None:
        return {}
    import json

    return cast(dict[str, str], json.loads(value))
