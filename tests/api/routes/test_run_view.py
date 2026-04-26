"""Tests for GET /runs/{run_id}/view route."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from waywarden.api.routes.run_view import router

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class _MockRunEvent:
    """Minimal mock RunEvent for route testing."""

    __slots__ = (
        "seq",
        "type",
        "payload",
        "id",
        "run_id",
        "timestamp",
        "causation",
        "actor",
    )

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
        self.timestamp = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        self.causation = None
        self.actor = None

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "seq": self.seq,
            "type": self.type,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "causation": None,
            "actor": None,
        }


class _MockRepo:
    """Minimal mock RunEventRepository for route testing."""

    def __init__(self, events: list[_MockRunEvent] | None = None) -> None:
        self.events: list[_MockRunEvent] = events or []

    async def append(self, event: Any) -> Any:
        self.events.append(event)  # type: ignore[arg-type]
        return event

    async def list(
        self,
        run_id: str,
        *,
        since_seq: int = 0,
        limit: int | None = None,
    ) -> list[_MockRunEvent]:
        return [e for e in self.events if e.run_id == run_id and e.seq > since_seq]

    async def latest_seq(self, run_id: str) -> int:
        matching = [e for e in self.events if e.run_id == run_id]
        return max((e.seq for e in matching), default=0)


def _inject_app(
    app: FastAPI,
    repo: _MockRepo,
    runs_repo: object | None = None,
) -> None:
    """Inject mock repos into the route's module-level state."""
    import waywarden.api.routes.run_view as route_mod

    route_mod._event_repo = repo
    route_mod._run_repo = runs_repo
    route_mod._manifest_repo = None


@pytest.fixture(autouse=True)
def _clean_state() -> None:
    """Drain repo state between tests."""
    import waywarden.api.routes.run_view as run_view_mod

    run_view_mod._event_repo = None
    run_view_mod._run_repo = None
    run_view_mod._manifest_repo = None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestViewReturnsSnapshot:
    """GET /runs/{id}/view returns the snapshot with milestones derived from run.progress events."""

    @pytest.mark.anyio
    async def test_view_returns_snapshot(self) -> None:
        """APPLY milestone events to the repo and validate the snapshot."""
        repo = _MockRepo(
            [
                _MockRunEvent(1, "run.progress", {"phase": "intake", "milestone": "received"}),
                _MockRunEvent(2, "run.progress", {"phase": "plan", "milestone": "drafted"}),
            ]
        )

        mock_runs = MagicMock()
        mock_run = MagicMock()
        mock_run.state = "planning"
        mock_runs.get = AsyncMock(return_value=mock_run)

        app = FastAPI()
        app.include_router(router)
        _inject_app(app, repo, runs_repo=mock_runs)

        client = TestClient(app)
        response = client.get("/runs/run-mock/view")

        assert response.status_code == 200
        body = response.json()
        assert body["run_state"] == "planning"
        assert len(body["milestones"]) == 2
        assert body["milestones"][0]["phase"] == "intake"
        assert body["milestones"][0]["milestone"] == "received"
        assert body["milestones"][1]["phase"] == "plan"
        assert body["milestones"][0]["description"] == "Task received and parsed by the harness"
        assert body["milestones"][1]["description"] == "Initial plan drafted"


class TestView404ForUnknownRun:
    """GET /runs/{id}/view returns 404 for unknown run ids."""

    @pytest.mark.anyio
    async def test_view_404_for_unknown_run(self) -> None:
        """The run repo returns None for unknown IDs."""
        repo = _MockRepo()

        mock_runs = MagicMock()
        mock_runs.get = AsyncMock(return_value=None)

        app = FastAPI()
        app.include_router(router)
        _inject_app(app, repo, runs_repo=mock_runs)

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/runs/unknown-run/view")

        assert response.status_code == 404
        body = response.json()
        assert "not found" in body["detail"]


class TestViewReturnsArtifactEvents:
    """Artifact events from run.artifact_created appear in snapshot."""

    @pytest.mark.anyio
    async def test_artifacts_reflected(self) -> None:
        """Artifact events are included in the snapshot."""
        repo = _MockRepo(
            [
                _MockRunEvent(
                    1,
                    "run.artifact_created",
                    {"artifact_kind": "usage-summary", "artifact_ref": "ref-1", "label": "tokens"},
                ),
            ]
        )

        mock_runs = MagicMock()
        mock_run = MagicMock()
        mock_run.state = "executing"
        mock_runs.get = AsyncMock(return_value=mock_run)

        app = FastAPI()
        app.include_router(router)
        _inject_app(app, repo, runs_repo=mock_runs)

        client = TestClient(app)
        response = client.get("/runs/run-mock/view")

        assert response.status_code == 200
        body = response.json()
        assert len(body["artifacts"]) == 1
        assert body["artifacts"][0]["artifact_kind"] == "usage-summary"
        assert body["artifacts"][0]["label"] == "tokens"
