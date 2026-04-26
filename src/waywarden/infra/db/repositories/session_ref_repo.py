"""SessionRefRepository implementation."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from waywarden.domain.session_reference import SessionReference
from waywarden.infra.db.models.session_ref import session_references


class SessionRefRepositoryImpl:
    """SQLAlchemy-backed persistence for coding-session references."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, ref: SessionReference) -> SessionReference:
        """Persist a new session reference."""
        stmt = session_references.insert().values(
            run_id=ref.run_id,
            artifact_id=ref.artifact_id,
            session_ref=ref.session_ref,
            created_at=ref.created_at,
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return ref

    async def get_by_run(self, run_id: str) -> Sequence[SessionReference]:
        """Return all session references for a run."""
        stmt = session_references.select().where(session_references.c.run_id == run_id)
        result = await self._session.execute(stmt)
        return [self._row_to_ref(row) for row in result.fetchall()]

    async def get_by_artifact(self, artifact_id: str) -> Sequence[SessionReference]:
        """Return all session references for an artifact."""
        stmt = session_references.select().where(session_references.c.artifact_id == artifact_id)
        result = await self._session.execute(stmt)
        return [self._row_to_ref(row) for row in result.fetchall()]

    async def get_by_key(self, run_id: str, artifact_id: str) -> SessionReference | None:
        """Return a specific reference by composite key."""
        stmt = session_references.select().where(
            session_references.c.run_id == run_id,
            session_references.c.artifact_id == artifact_id,
        )
        result = await self._session.execute(stmt)
        row = result.fetchone()
        if row is None:
            return None
        return self._row_to_ref(row)

    async def remove(self, run_id: str) -> int:
        """Remove all session references for a run."""
        stmt = session_references.delete().where(session_references.c.run_id == run_id)
        result = await self._session.execute(stmt)
        return result.rowcount  # type: ignore[attr-defined,no-any-return]

    @staticmethod
    def _row_to_ref(row: object) -> SessionReference:
        """Convert a database RowProxy to a SessionReference."""
        return SessionReference(
            run_id=row.run_id,  # type: ignore[attr-defined]
            artifact_id=row.artifact_id,  # type: ignore[attr-defined]
            session_ref=row.session_ref,  # type: ignore[attr-defined]
            created_at=row.created_at,  # type: ignore[attr-defined]
        )
