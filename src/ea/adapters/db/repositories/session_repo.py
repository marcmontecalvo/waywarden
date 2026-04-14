from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ea.adapters.db.models import SessionRecord


class SessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_or_create(self, session_id: str) -> SessionRecord:
        result = await self._db.execute(
            select(SessionRecord).where(SessionRecord.id == session_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            record = SessionRecord(id=session_id)
            self._db.add(record)
            await self._db.commit()
        return record
