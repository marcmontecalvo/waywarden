"""GET /runs/{run_id}/events — SSE stream for client surfaces.

Honours RT-002 §Reconnect semantics: clients pass ``last_seen_seq``, the server
returns every event where ``seq > last_seen_seq``, and the connection stays open
to tail new events until a terminal event lands.

Module-level mutable references (_event_repo) allow test injection.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import anyio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from waywarden.api.streaming.sse import (
    _json_sse_frame,
    _subscribe,
    _unsubscribe,
    create_sse_response,
)
from waywarden.domain.repositories import RunEventRepository

router = APIRouter(tags=["run-events"])

# -- Dependency injection (set in test harness or app startup) ---------------

_event_repo: RunEventRepository | None = None
_terminal_states: frozenset[str] = frozenset({"completed", "failed", "cancelled"})


def _get_event_repo() -> RunEventRepository | None:
    return _event_repo


@router.get(
    "/runs/{run_id}/events",
    summary="Stream run events as SSE",
)
async def run_events_stream(
    run_id: str,
    last_seen_seq: int = 0,
) -> StreamingResponse:
    """SSE endpoint honouring RT-002 reconnect semantics.

    Sequence:
    1. Resolve ``latest_seq(run_id)`` from the repository.
    2. If ``last_seen_seq > latest_seq``, return 400.
    3. Emit all persisted events with ``seq > last_seen_seq`` in ascending order.
    4. Subscribe to the in-process pub/sub and tail new events until terminal.
    """
    repo = _get_event_repo()

    if repo is None:
        raise HTTPException(status_code=503, detail="event repository not configured")

    # Exhaustive check to satisfy mypy
    assert repo is not None

    # Validate reconnect parameter
    latest = await _latest_seq_safe(run_id, repo)
    if last_seen_seq > latest:
        raise HTTPException(
            status_code=400,
            detail=f"last_seen_seq ({last_seen_seq}) exceeds latest seq ({latest})",
        )

    return create_sse_response(
        _build_stream(run_id, last_seen_seq, latest, repo),
    )


# ---------------------------------------------------------------------------
# Stream helpers
# ---------------------------------------------------------------------------


async def _latest_seq_safe(run_id: str, repo: RunEventRepository) -> int:
    """Get latest seq; return 0 on any error."""
    try:
        return await repo.latest_seq(run_id)
    except Exception:
        return 0


async def _build_stream(
    run_id: str,
    last_seen_seq: int,
    latest: int,
    repo: RunEventRepository,
) -> AsyncGenerator[bytes]:
    """Replay then tail events until terminal or stream closed."""
    try:
        # Phase 1 — replay existing events
        events = await repo.list(run_id, since_seq=last_seen_seq)

        emitted_seqs: set[int] = set()
        for ev in events:
            if ev.seq in emitted_seqs:
                continue
            emitted_seqs.add(ev.seq)
            yield _json_sse_frame(ev)
            if ev.type in _terminal_states:
                return  # terminal event closes the stream

        # Phase 2 — tail new events via in-process pub/sub
        subscriber = _subscribe(run_id)
        try:
            while True:
                await subscriber.wait()
                # Re-query for new events since our highest emitted seq
                cutoff = max(last_seen_seq, max(emitted_seqs)) if emitted_seqs else 0
                new_events = await repo.list(run_id, since_seq=cutoff)
                for ev in new_events:
                    if ev.seq in emitted_seqs:
                        continue
                    emitted_seqs.add(ev.seq)
                    yield _json_sse_frame(ev)
                    if ev.type in _terminal_states:
                        return
                # Clear event to re-wait
                subscriber.event = anyio.Event()
        finally:
            _unsubscribe(run_id, subscriber)
    except GeneratorExit:
        return
    except Exception:
        return
