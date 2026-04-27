"""Tests for GET /runs/{run_id}/events SSE stream endpoint.

Tests generator logic directly to avoid blocking on the tail phase,
and TestClient for the 400 validation path.
"""

from __future__ import annotations

import json
from typing import Any, cast

import anyio
import pytest
from fastapi import FastAPI

from waywarden.api.routers.run_events import router

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class _MockRunEvent:
    """Minimal mock RunEvent for SSE endpoint testing."""

    __slots__ = ("seq", "type", "payload", "id", "run_id", "timestamp", "causation", "actor")

    def __init__(
        self,
        seq: int,
        type_: str,
        payload: dict[str, Any] | None = None,
        *,
        id_: str = "evt-mock",
        run_id: str = "run-mock",
    ) -> None:
        self.seq = seq
        self.type = type_
        self.payload = payload or {}
        self.id = id_
        self.run_id = run_id
        self.timestamp = None
        self.causation = None
        self.actor = None

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Expose an API-compatible transformer for SSE encoding."""
        return {
            "id": self.id,
            "run_id": self.run_id,
            "seq": self.seq,
            "type": self.type,
            "payload": self.payload,
            "timestamp": None,
            "causation": None,
            "actor": None,
        }


class _MockRepo:
    """Mock RunEventRepository for SSE endpoint testing."""

    def __init__(self, events: list[_MockRunEvent] | None = None) -> None:
        self.events: list[_MockRunEvent] = events or []
        self._called_with: list[dict[str, Any]] = []

    async def append(self, event: Any) -> Any:  # noqa: ANN401
        self.events.append(event)
        return event

    async def list(
        self,
        run_id: str,
        *,
        since_seq: int = 0,
        limit: int | None = None,
    ) -> list[_MockRunEvent]:
        self._called_with.append(
            {"run_id": run_id, "since_seq": since_seq, "limit": limit},
        )
        return [e for e in self.events if e.run_id == run_id and e.seq > since_seq]

    async def latest_seq(self, run_id: str) -> int:
        matching = [e for e in self.events if e.run_id == run_id]
        return max((e.seq for e in matching), default=0)


@pytest.fixture(autouse=True)
def _clean_state() -> None:
    """Drain pub/sub and repo state between tests."""
    import waywarden.api.routers.run_events as re_mod
    import waywarden.api.streaming.sse as sse_mod

    sse_mod._publisher_subscribers.clear()
    re_mod._event_repo = None


async def _attach_repo(repo: _MockRepo) -> None:
    """Inject a mock repo into the module-level reference."""
    import waywarden.api.routers.run_events as re_mod

    re_mod._event_repo = cast(Any, repo)


async def _collect_frames(
    gen: Any,
    timeout: float = 2.0,
) -> list[dict[str, Any]]:
    """Collect JSON frames from an async generator with a hard timeout."""
    results: list[dict[str, Any]] = []

    async def _main() -> None:
        async for frame in gen:
            parsed = _frame_to_json(frame)
            if parsed is not None:
                results.append(parsed)

    # anyio.move_on_after cancels the inner context after timeout
    with anyio.move_on_after(timeout):
        await _main()

    return results


def _frame_to_json(frame: bytes) -> dict[str, Any] | None:
    """Extract JSON object from a raw SSE data frame."""
    text = frame.decode("utf-8")
    for line in text.split("\n"):
        if line.startswith("data: "):
            return cast(dict[str, Any], json.loads(line[len("data: ") :]))
    return None


def _parse_events(payload: bytes) -> list[dict[str, Any]]:
    """Parse all JSON data objects from an SSE response payload."""
    lines = payload.decode("utf-8").split("\n")
    result: list[dict[str, Any]] = []
    for line in lines:
        if line.startswith("data: "):
            result.append(cast(dict[str, Any], json.loads(line[len("data: ") :])))
    return result


# ---------------------------------------------------------------------------
# Test: Replay from zero
# ---------------------------------------------------------------------------


class TestReplayFromZero:
    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_replay_from_zero(self) -> None:
        """Generator yields exactly 3 events when replaying from seq=0."""
        event1 = _MockRunEvent(seq=1, type_="run.created")
        event2 = _MockRunEvent(seq=2, type_="run.progress")
        event3 = _MockRunEvent(seq=3, type_="run.progress")

        repo = _MockRepo([event1, event2, event3])
        await _attach_repo(repo)

        from waywarden.api.routers.run_events import _build_stream

        gen = _build_stream("run-mock", 0, 3, cast(Any, repo))
        events = await _collect_frames(gen)

        assert len(events) == 3
        assert events[0]["seq"] == 1
        assert events[0]["type"] == "run.created"
        assert events[1]["seq"] == 2
        assert events[2]["seq"] == 3

        assert len(repo._called_with) >= 1
        assert repo._called_with[0]["since_seq"] == 0


# ---------------------------------------------------------------------------
# Test: Replay from N
# ---------------------------------------------------------------------------


class TestReplayFromN:
    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_replay_from_n(self) -> None:
        """last_seen_seq=2 emits only the third event."""
        event1 = _MockRunEvent(seq=1, type_="run.created")
        event2 = _MockRunEvent(seq=2, type_="run.progress")
        third_event = _MockRunEvent(
            seq=3,
            type_="run.progress",
            payload={"phase": "execute"},
        )

        repo = _MockRepo([event1, event2, third_event])
        await _attach_repo(repo)

        from waywarden.api.routers.run_events import _build_stream

        gen = _build_stream("run-mock", 2, 3, cast(Any, repo))
        events = await _collect_frames(gen)

        assert len(events) == 1
        assert events[0]["seq"] == 3
        assert events[0]["type"] == "run.progress"

        assert repo._called_with[0]["since_seq"] == 2


# ---------------------------------------------------------------------------
# Test: Invalid last_seen_seq returns 400
# ---------------------------------------------------------------------------


class TestInvalidLastSeenSeqReturns400:
    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_invalid_last_seen_seq_returns400(self) -> None:
        """last_seen_seq greater than latest_seq returns 400."""
        repo = _MockRepo()
        await _attach_repo(repo)

        app = FastAPI()
        app.include_router(router)
        from starlette.testclient import TestClient

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/runs/run-mock/events?last_seen_seq=10")
        assert response.status_code == 400
        body = response.json()
        assert "exceeds latest" in body["detail"]

        assert repo._called_with == []


# ---------------------------------------------------------------------------
# Test: Terminal event closes stream
# ---------------------------------------------------------------------------


class TestTerminalEventClosesStream:
    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_terminal_event_closes_stream(self) -> None:
        """Stream closes after a terminal event (generator returns cleanly)."""
        completed_event = _MockRunEvent(
            seq=1,
            type_="run.completed",
            payload={"outcome": "success"},
        )

        repo = _MockRepo([completed_event])
        await _attach_repo(repo)

        from waywarden.api.routers.run_events import _build_stream

        gen = _build_stream("run-mock", 0, 1, cast(Any, repo))
        events = await _collect_frames(gen)

        # Terminal event closes stream — generator returns, no tail blocking
        assert len(events) == 1
        assert events[0]["type"] == "run.completed"

        assert repo._called_with[0]["since_seq"] == 0


# ---------------------------------------------------------------------------
# Test: Reconnect after terminal
# ---------------------------------------------------------------------------


class TestReconnectAfterTerminalReturnsEmpty:
    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_reconnect_after_terminal_returns_empty_then_closes(
        self,
    ) -> None:
        """Reconnecting with last_seen_seq=N (terminal seq) gives empty response."""
        terminal_event = _MockRunEvent(
            seq=5,
            type_="run.failed",
            payload={"reason": "timeout"},
        )

        repo = _MockRepo([terminal_event])
        await _attach_repo(repo)

        from waywarden.api.routers.run_events import _build_stream

        gen = _build_stream("run-mock", 5, 5, cast(Any, repo))
        events = await _collect_frames(gen)

        assert events == []

        assert repo._called_with[0]["since_seq"] == 5


# ---------------------------------------------------------------------------
# Integration test: full HTTP round-trip (non-streaming validation paths)
# ---------------------------------------------------------------------------


class TestHttp400RoundTrip:
    """Validate the 400 error path works end-to-end over HTTP."""

    @pytest.mark.integration
    def test_full_400_roundtrip(self) -> None:
        """HTTP GET with last_seen_seq > latest_seq returns 400 with JSON body."""
        repo = _MockRepo()

        import waywarden.api.routers.run_events as re_mod

        re_mod._event_repo = cast(Any, repo)

        from starlette.testclient import TestClient

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        response = client.get("/runs/run-mock/events?last_seen_seq=99")

        assert response.status_code == 400
        body = response.json()
        assert "exceeds latest" in body["detail"]
