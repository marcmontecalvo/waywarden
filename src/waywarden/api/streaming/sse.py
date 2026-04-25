"""SSE response helpers for event-stream endpoints.

Provides an async generator protocol and a helper streaming response wrapper.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

import anyio
from fastapi.responses import StreamingResponse

# ---------------------------------------------------------------------------
# SSE frame helpers
# ---------------------------------------------------------------------------


def _json_sse_frame(event: Any) -> bytes:  # noqa: ANN401
    """Format a single SSE data frame containing an event as JSON."""
    mode: str = "json"
    default: Any = str
    return (
        f"id: {event.seq}\ndata: {json.dumps(event.model_dump(mode=mode, default=default))}\n\n\n"
    ).encode()


async def _stream_pages() -> AsyncGenerator[bytes]:
    """Never-ending heartbeat stream so the client knows the connection is alive.

    Emits ``:`` comment frames every 15 seconds.
    """
    while True:
        await anyio.sleep(15)
        yield b":\r\n\r\n"


# ---------------------------------------------------------------------------
# In-process pub/sub for SSE tailing
# ---------------------------------------------------------------------------


class _Subscriber:
    """RAII-style subscriber handle for a single run ID."""

    __slots__ = ("event",)

    def __init__(self) -> None:
        self.event = anyio.Event()

    async def wait(self) -> None:
        self.event = anyio.Event()
        await self.event.wait()

    def notify(self) -> None:
        self.event.set()

    def __repr__(self) -> str:
        return f"<_Subscriber event={self.event}>"


_publisher_subscribers: dict[str, list[_Subscriber]] = {}


def _subscribe(run_id: str) -> _Subscriber:
    """Register a subscriber for *run_id* and return the handle."""
    if run_id not in _publisher_subscribers:
        _publisher_subscribers[run_id] = []
    sub = _Subscriber()
    _publisher_subscribers[run_id].append(sub)
    return sub


def _publish(run_id: str) -> None:
    """Notify all subscribers for *run_id*."""
    subs = _publisher_subscribers.get(run_id, [])
    for sub in subs:
        sub.notify()


def _unsubscribe(run_id: str, sub: _Subscriber) -> None:
    """Remove *sub* from the subscriber list for *run_id*."""
    subs = _publisher_subscribers.get(run_id, [])
    if sub in subs:
        subs.remove(sub)
    if not subs:
        _publisher_subscribers.pop(run_id, None)


# ---------------------------------------------------------------------------
# StreamingResponse wrapper
# ---------------------------------------------------------------------------


def create_sse_response(
    async_gen: AsyncGenerator[bytes],
    media_type: str = "text/event-stream",
) -> StreamingResponse:
    """Wrap an async generator in a StreamingResponse with SSE headers."""
    return StreamingResponse(
        content=async_gen,
        media_type=media_type,
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
