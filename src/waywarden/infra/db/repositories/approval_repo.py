"""ApprovalRepository implementation."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from waywarden.domain.approval import Approval
from waywarden.infra.db.models.approval import approvals


class ApprovalRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, id: str) -> Approval | None:
        stmt = approvals.select().where(approvals.c.id == id)
        result = await self._session.execute(stmt)
        row = result.fetchone()
        if row is None:
            return None
        return Approval(
            id=row.id,
            run_id=row.run_id,
            approval_kind=row.approval_kind,
            requested_capability=row.requested_capability,
            summary=row.summary,
            state=row.state,
            requested_at=_parse_ts(row.requested_at),
            decided_at=_parse_ts(row.decided_at) if row.decided_at else None,
            decided_by=row.decided_by,
            expires_at=_parse_ts(row.expires_at) if row.expires_at else None,
        )

    async def save(self, approval: Approval) -> Approval:
        stmt = approvals.insert().values(
            id=approval.id,
            run_id=approval.run_id,
            approval_kind=approval.approval_kind,
            requested_capability=approval.requested_capability,
            summary=approval.summary,
            state=approval.state,
            requested_at=approval.requested_at,
            decided_at=approval.decided_at if approval.decided_at else None,
            decided_by=approval.decided_by,
            expires_at=approval.expires_at if approval.expires_at else None,
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return approval

    async def list_by_run(self, run_id: str) -> list[Approval]:
        stmt = approvals.select().where(approvals.c.run_id == run_id)
        result = await self._session.execute(stmt)
        rows = result.fetchall()
        return [
            Approval(
                id=r.id,
                run_id=r.run_id,
                approval_kind=r.approval_kind,
                requested_capability=r.requested_capability,
                summary=r.summary,
                state=r.state,
                requested_at=_parse_ts(r.requested_at),
                decided_at=_parse_ts(r.decided_at) if r.decided_at else None,
                decided_by=r.decided_by,
                expires_at=_parse_ts(r.expires_at) if r.expires_at else None,
            )
            for r in rows
        ]


def _parse_ts(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    return datetime.fromisoformat(value)
