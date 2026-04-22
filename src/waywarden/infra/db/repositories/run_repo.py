"""RunRepository implementation."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from waywarden.domain.run import Run
from waywarden.infra.db.models.run import runs


class RunRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, run: Run) -> Run:
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
        await self._session.execute(stmt)
        await self._session.flush()
        return run

    async def get(self, run_id: str) -> Run | None:
        stmt = runs.select().where(runs.c.id == run_id)
        result = await self._session.execute(stmt)
        row = result.fetchone()
        if row is None:
            return None
        return Run(
            id=row.id,
            instance_id=row.instance_id,
            task_id=row.task_id,
            profile=row.profile,
            policy_preset=row.policy_preset,
            manifest_ref=row.manifest_ref,
            entrypoint=row.entrypoint,
            state=row.state,
            created_at=_parse_ts(row.created_at),
            updated_at=_parse_ts(row.updated_at),
            terminal_seq=row.terminal_seq,
        )

    async def load_latest_state(self, run_id: str) -> Run | None:
        """Return the most recent persisted Run for *run_id*."""
        return await self.get(run_id)

    async def update_state(
        self,
        run_id: str,
        new_state: str,
        terminal_seq: int | None,
    ) -> Run:
        """Update the state and terminal_seq of an existing run."""
        stmt = (
            runs.update()
            .where(runs.c.id == run_id)
            .values(
                state=new_state,
                updated_at=datetime.now(UTC),
                terminal_seq=terminal_seq,
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()
        result = await self.get(run_id)
        if result is None:
            raise RuntimeError(f"Run {run_id} disappeared after update_state")
        return result


def _parse_ts(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    return datetime.fromisoformat(value)
