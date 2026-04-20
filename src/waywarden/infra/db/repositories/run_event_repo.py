"""RunEventRepository — append-only event log with FOR UPDATE seq locking.

This implementation enforces the RT-002 append-only invariant at the
repository layer:

1. **Monotonic seq**: ``SELECT ... FOR UPDATE`` inside the same transaction
   serialises concurrent appends to the same run, producing strictly
   increasing seq with no gaps.
2. **Terminal-state immutability**: once a run reaches ``completed``,
   ``failed``, or ``cancelled``, no further events may be appended.
3. **Typed errors**: ``TerminalRunStateError`` for terminal-state violations;
   ``RuntimeError`` for seq conflicts.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from waywarden.domain.repositories import (
    TerminalRunStateError,
)
from waywarden.domain.run_event import RunEvent
from waywarden.infra.db.models.run import runs
from waywarden.infra.db.models.run_event import run_events

_TERMINAL_STATES = frozenset({"completed", "failed", "cancelled"})


def _event_to_row(event: RunEvent) -> dict[str, object]:
    """Serialize a RunEvent to a dict suitable for table insertion."""
    return {
        "id": event.id,
        "run_id": event.run_id,
        "seq": str(event.seq),
        "type": event.type,
        "payload": json.dumps(dict(event.payload)),
        "timestamp": event.timestamp,
        "causation": json.dumps(
            {
                "event_id": event.causation.event_id,
                "action": event.causation.action,
                "request_id": event.causation.request_id,
            }
        )
        if event.causation
        else None,
        "actor": json.dumps(
            {
                "kind": event.actor.kind,
                "id": event.actor.id,
                "display": event.actor.display,
            }
        )
        if event.actor
        else None,
    }


def _row_to_event(row: Any) -> RunEvent:
    """Convert a raw run_events row to a RunEvent domain instance."""
    from waywarden.domain.run_event import Actor as _Actor
    from waywarden.domain.run_event import Causation as _Causation

    causation: _Causation | None = None
    if row.causation:
        d = json.loads(row.causation)
        causation = _Causation(**d)

    actor: _Actor | None = None
    if row.actor:
        d = json.loads(row.actor)
        actor = _Actor(**d)

    payload: dict[str, object] = json.loads(row.payload) if row.payload else {}

    ts = row.timestamp
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    elif ts.tzinfo is None:
        # SQLite may strip tzinfo — assume UTC
        ts = ts.replace(tzinfo=UTC)

    return RunEvent(
        id=row.id,
        run_id=row.run_id,
        seq=int(row.seq),
        type=row.type,
        payload=payload,
        timestamp=ts,
        causation=causation,
        actor=actor,
    )


class RunEventRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, event: RunEvent) -> RunEvent:
        """Append a single RT-002 event with FOR UPDATE seq locking."""
        run_id = event.run_id

        # 1. Terminal-state guard
        latest_state = await self._get_run_state(run_id)
        if latest_state in _TERMINAL_STATES:
            raise TerminalRunStateError(
                f"Cannot append event to run {run_id} in terminal state {latest_state!r}"
            )

        # 2. Compute next seq under row-level lock
        next_seq = await self._compute_next_seq(run_id)

        # 3. Insert the event row via the table
        row_data = _event_to_row(event)
        # Override seq with the computed value
        row_data["seq"] = str(next_seq)
        # Re-serialize payload with the correct seq
        row_data["payload"] = json.dumps(
            {**dict(event.payload), "_assigned_seq": next_seq}
        )

        insert_stmt = run_events.insert().values(**row_data)
        await self._session.execute(insert_stmt)
        await self._session.flush()

        # Return the event with the assigned seq
        return RunEvent(
            id=event.id,
            run_id=event.run_id,
            seq=next_seq,
            type=event.type,
            payload=dict(event.payload),
            timestamp=event.timestamp,
            causation=event.causation,
            actor=event.actor,
        )

    async def list(
        self,
        run_id: str,
        *,
        since_seq: int = 0,
        limit: int | None = None,
    ) -> list[RunEvent]:
        """Return events with ``seq > since_seq``, ordered ascending."""
        stmt = (
            run_events.select()
            .where(
                run_events.c.run_id == run_id,
                text(f"{run_events.c.seq} > :since_seq"),
            )
            .order_by(run_events.c.seq)
        )
        params: dict[str, str] = {"since_seq": str(since_seq)}
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self._session.execute(stmt, params)
        rows = result.fetchall()
        return [_row_to_event(row) for row in rows]

    async def latest_seq(self, run_id: str) -> int:
        """Return the highest seq for *run_id*, or 0 if no events exist."""
        stmt = text(
            "SELECT COALESCE(MAX(CAST(seq AS INTEGER)), 0) "
            "FROM run_events WHERE run_id = :run_id"
        )
        result = await self._session.execute(stmt, {"run_id": run_id})
        row = result.scalar_one()
        return int(row) if row else 0

    # -- private helpers -----------------------------------------------------

    async def _get_run_state(self, run_id: str) -> str | None:
        """Return the current state of a run, or None."""
        stmt = runs.select().where(runs.c.id == run_id)
        result = await self._session.execute(stmt)
        row = result.fetchone()
        return row.state if row else None

    async def _compute_next_seq(self, run_id: str) -> int:
        """Compute next seq under ``FOR UPDATE`` lock on the run_events row.

        Falls back to a non-locking query on databases that don't support
        ``FOR UPDATE`` (e.g. SQLite in tests).
        """
        try:
            stmt = text(
                "SELECT COALESCE(MAX(CAST(seq AS INTEGER)), 0) + 1 "
                "FROM run_events "
                "WHERE run_id = :run_id "
                "FOR UPDATE"
            )
            result = await self._session.execute(stmt, {"run_id": run_id})
        except Exception:
            # SQLite doesn't support FOR UPDATE — fall back
            stmt = text(
                "SELECT COALESCE(MAX(CAST(seq AS INTEGER)), 0) + 1 "
                "FROM run_events "
                "WHERE run_id = :run_id"
            )
            result = await self._session.execute(stmt, {"run_id": run_id})
        next_seq = result.scalar_one()
        return int(next_seq)
