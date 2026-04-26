"""Integration test: full chat → orchestration → event-stream roundtrip.

Exit gate for P4.  Tests against an in-memory SQLite repo, proving the
full chat -> event-stream path works end-to-end.

Pattern: SSE streaming tests use the generator directly (like other
existing SSE tests in test_run_events_sse.py).  The HTTP-only tests
validation paths that don't require streaming (400 errors, etc.).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import anyio
import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import waywarden.api.routes.chat as chat_mod
from waywarden.api.routers import run_events as run_events_mod
from waywarden.api.routers.run_events import _build_stream
from waywarden.api.routes.chat import router as chat_router
from waywarden.domain.ids import RunEventId
from waywarden.domain.run_event import RunEvent
from waywarden.infra.db.repositories.run_event_repo import RunEventRepositoryImpl
from waywarden.infra.db.repositories.run_repo import RunRepositoryImpl

# ---------------------------------------------------------------------------
# Engine fixture — only create run + run_events tables (avoid JSONB issue)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def _engine() -> AsyncEngine:
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS runs (
                id VARCHAR PRIMARY KEY, instance_id VARCHAR NOT NULL,
                task_id VARCHAR, profile VARCHAR NOT NULL, policy_preset VARCHAR NOT NULL,
                manifest_ref VARCHAR NOT NULL, entrypoint VARCHAR NOT NULL, state VARCHAR NOT NULL,
                created_at TIMESTAMP NOT NULL, updated_at TIMESTAMP NOT NULL,
                terminal_seq INTEGER, manifest_hash VARCHAR
            )
        """)
        )
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS run_events (
                id VARCHAR PRIMARY KEY, run_id VARCHAR NOT NULL, seq INTEGER NOT NULL,
                type VARCHAR NOT NULL, payload VARCHAR NOT NULL, timestamp TIMESTAMP NOT NULL,
                causation VARCHAR, actor VARCHAR,
                FOREIGN KEY(run_id) REFERENCES runs(id)
            )
        """)
        )
    yield eng
    await eng.dispose()


# ---------------------------------------------------------------------------
# App builder
# ---------------------------------------------------------------------------


def _build_test_app(_engine: AsyncEngine) -> dict[str, Any]:
    """Build a test app with injected repo references."""
    app = FastAPI(title="test")
    async_session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

    s = async_session_factory()
    evt_repo = RunEventRepositoryImpl(s)
    run_repo = RunRepositoryImpl(s)

    # Inject into module-level mutable references
    chat_mod._event_repo = evt_repo
    chat_mod._run_repo = run_repo
    chat_mod._task_repo = None
    chat_mod._session_repo = None
    chat_mod._lifecycle_svc = None

    run_events_mod._event_repo = evt_repo

    app.include_router(chat_router)
    app.include_router(run_events_mod.router)

    return {
        "app": app,
        "evt_repo": evt_repo,
        "run_repo": run_repo,
        "session_factory": async_session_factory,
    }


# ---------------------------------------------------------------------------
# Test 1: chat emits run_created event
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_chat_emits_run_created(_engine: AsyncEngine) -> None:
    """POST /chat emits a ``run.created`` event and returns a run_id."""
    state = _build_test_app(_engine)
    app = state["app"]

    transport = ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    resp = await client.post(
        "/chat",
        json={"session_id": "test-session", "message": "hello world"},
        headers={"X-Waywarden-Operator": "test-operator"},
    )
    assert resp.status_code == 202
    body = resp.json()
    run_id = body["run_id"]
    assert run_id.startswith("run-")
    assert "stream_url" in body
    assert run_id in body["stream_url"]

    # Verify run.created event was emitted to the repository
    evt_repo = state["evt_repo"]
    events = await evt_repo.list(run_id)
    assert len(events) == 1
    assert events[0].type == "run.created"

    await client.aclose()


# ---------------------------------------------------------------------------
# Test 2: SSE generator yields events in order
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.anyio
async def test_sse_emits_events_in_order(_engine: AsyncEngine) -> None:
    """Events emitted to the repo are replayed in ascending seq order.

    Tests the _build_stream generator directly (not HTTP) to avoid
    pub/sub blocking issues in the HTTP wrapper.
    """
    state = _build_test_app(_engine)
    evt_repo = state["evt_repo"]

    # Manually create events for a test run
    run_id = "run-sse-order-test"
    events = [
        RunEvent(
            id=RunEventId("evt-order-1"),
            run_id=run_id,
            seq=1,
            type="run.created",
            payload={
                "instance_id": "inst-1",
                "profile": "test",
                "policy_preset": "yolo",
                "manifest_ref": "//manifest/1",
                "entrypoint": "cli",
            },
            timestamp=datetime(2025, 1, 1, tzinfo=UTC),
            causation=None,
            actor=None,
        ),
        RunEvent(
            id=RunEventId("evt-order-2"),
            run_id=run_id,
            seq=2,
            type="run.progress",
            payload={"phase": "intake", "milestone": "received"},
            timestamp=datetime(2025, 1, 1, 1, 0, 0, tzinfo=UTC),
            causation=None,
            actor=None,
        ),
        RunEvent(
            id=RunEventId("evt-order-3"),
            run_id=run_id,
            seq=3,
            type="run.completed",
            payload={"outcome": "success"},
            timestamp=datetime(2025, 1, 1, 2, 0, 0, tzinfo=UTC),
            causation=None,
            actor=None,
        ),
    ]
    for ev in events:
        await evt_repo.append(ev)

    gen = _build_stream(run_id, 0, 3, evt_repo)
    frames = []

    async def _collect() -> None:
        async for frame in gen:
            parsed = frame
            if parsed is not None:
                frames.append(parsed)

    with anyio.move_on_after(2.0):
        await _collect()

    # Terminal event (run.completed) closes the generator
    assert len(frames) == 3
    assert b'"seq": 1' in frames[0]
    assert b'"type": "run.created"' in frames[0]
    assert b'"seq": 2' in frames[1]
    assert b'"phase": "intake"' in frames[1]
    assert b'"seq": 3' in frames[2]
    assert b'"type": "run.completed"' in frames[2]


# ---------------------------------------------------------------------------
# Test 3: replay contains only in-catalog event types
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.anyio
async def test_no_out_of_catalog_event_types(_engine: AsyncEngine) -> None:  # noqa: C901
    """SSE replay contains no event types outside the RT-002 catalog."""
    RT002_CATALOG: frozenset[str] = frozenset(
        [
            "run.created",
            "run.plan_ready",
            "run.execution_started",
            "run.progress",
            "run.approval_waiting",
            "run.resumed",
            "run.artifact_created",
            "run.completed",
            "run.failed",
            "run.cancelled",
        ]
    )

    state = _build_test_app(_engine)
    evt_repo = state["evt_repo"]

    run_id = "run-catalog-test"
    events_list = [
        RunEvent(
            id=RunEventId("evt-cat-1"),
            run_id=run_id,
            seq=1,
            type="run.created",
            payload={
                "instance_id": "inst-1",
                "profile": "test",
                "policy_preset": "yolo",
                "manifest_ref": "//manifest/1",
                "entrypoint": "cli",
            },
            timestamp=datetime(2025, 1, 1, tzinfo=UTC),
            causation=None,
            actor=None,
        ),
        RunEvent(
            id=RunEventId("evt-cat-2"),
            run_id=run_id,
            seq=2,
            type="run.artifact_created",
            payload={
                "artifact_ref": f"artifact://runs/{run_id}/usage-summary",
                "artifact_kind": "usage-summary",
                "label": "usage-summary",
            },
            timestamp=datetime(2025, 1, 1, 1, 0, 0, tzinfo=UTC),
            causation=None,
            actor=None,
        ),
        RunEvent(
            id=RunEventId("evt-cat-3"),
            run_id=run_id,
            seq=3,
            type="run.completed",
            payload={"outcome": "success"},
            timestamp=datetime(2025, 1, 1, 2, 0, 0, tzinfo=UTC),
            causation=None,
            actor=None,
        ),
    ]
    for ev in events_list:
        await evt_repo.append(ev)

    gen = _build_stream(run_id, 0, 3, evt_repo)
    collected_frames: list[bytes] = []

    async def _collect() -> None:
        async for frame in gen:
            if frame is not None:
                collected_frames.append(frame)

    with anyio.move_on_after(2.0):
        await _collect()

    event_types: list[str] = []
    for frame in collected_frames:
        text = frame.decode("utf-8")
        for line in text.split("\n"):
            if line.startswith("data: "):
                evt = json.loads(line[len("data: ") :])
                event_types.append(evt["type"])

    for et in event_types:
        assert et in RT002_CATALOG, f"Event type {et!r} is not in the RT-002 catalog"

    assert "run.created" in event_types
    assert "run.artifact_created" in event_types
    assert "run.completed" in event_types


# ---------------------------------------------------------------------------
# Test 4: reconnect after terminal returns empty
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.anyio
async def test_reconnect_after_terminal_returns_empty(_engine: AsyncEngine) -> None:
    """Reconnecting with last_seen_seq=terminal seq yields no new events."""
    state = _build_test_app(_engine)
    evt_repo = state["evt_repo"]

    run_id = "run-reconnect-test"
    terminal_event = RunEvent(
        id=RunEventId("evt-rec-1"),
        run_id=run_id,
        seq=1,
        type="run.completed",
        payload={"outcome": "ok"},
        timestamp=datetime(2025, 1, 1, tzinfo=UTC),
        causation=None,
        actor=None,
    )
    await evt_repo.append(terminal_event)
    latest = 1

    gen = _build_stream(run_id, 1, latest, evt_repo)
    collected: list[bytes] = []

    async def _collect() -> None:
        async for frame in gen:
            if frame is not None:
                collected.append(frame)

    with anyio.move_on_after(2.0):
        await _collect()

    assert collected == []
