"""Tests for the POST /chat route."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from waywarden.api.routes.chat import router


def _make_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


class TestHappyPathReturnsRunId:
    @pytest.mark.integration
    async def test_happy_path_returns_run_id(self) -> None:
        """On valid input with auth header, returns 202 with run_id and stream_url."""
        mock_repo = MagicMock()
        mock_repo.latest_seq = AsyncMock(return_value=0)
        mock_repo.append = AsyncMock(return_value={})

        import waywarden.api.routes.chat as chat_mod

        chat_mod._event_repo = mock_repo

        app = _make_test_app()
        client = TestClient(app, raise_server_exceptions=False)

        response = client.post(
            "/chat",
            json={
                "session_id": "session-1",
                "message": "Hello, world!",
                "manifest_ref": "manifest://v1",
                "policy_preset": "yolo",
            },
            headers={"X-Waywarden-Operator": "incoming-like"},
        )

        assert response.status_code in (200, 202)
        body = response.json()
        assert "run_id" in body
        assert "stream_url" in body
        assert body["stream_url"].startswith("/api/runs/")
        assert "last_seen_seq=0" in body["stream_url"]

        # Verify event was persisted
        mock_repo.append.assert_called_once()


class TestUnknownFieldsRejected:
    async def test_unknown_fields_rejected(self) -> None:
        """Unknown body fields return 422 (pydantic v2)."""
        import waywarden.api.routes.chat as chat_mod

        fake_repo = MagicMock()
        chat_mod._event_repo = fake_repo

        app = _make_test_app()
        client = TestClient(app, raise_server_exceptions=False)

        response = client.post(
            "/chat",
            json={
                "session_id": "session-1",
                "message": "Hello",
                "magic_field": "should be rejected",
            },
            headers={"X-Waywarden-Operator": "incoming-like"},
        )

        assert response.status_code == 422


class TestMissingOperatorHeaderRejected:
    async def test_missing_operator_header_rejected(self) -> None:
        """Missing X-Waywarden-Operator returns 401."""
        import waywarden.api.routes.chat as chat_mod

        fake_repo = MagicMock()
        chat_mod._event_repo = fake_repo

        app = _make_test_app()
        client = TestClient(app, raise_server_exceptions=False)

        response = client.post(
            "/chat",
            json={
                "session_id": "session-1",
                "message": "Hello",
            },
        )

        assert response.status_code == 401


class TestRunCreatedEventPersisted:
    @pytest.mark.integration
    async def test_run_created_event_persisted(self) -> None:
        """A run.created event is visible after POST."""
        mock_repo = MagicMock()
        mock_repo.latest_seq = AsyncMock(return_value=0)
        mock_repo.append = AsyncMock(return_value=None)

        import waywarden.api.routes.chat as chat_mod

        chat_mod._event_repo = mock_repo

        app = _make_test_app()
        client = TestClient(app, raise_server_exceptions=False)

        response = client.post(
            "/chat",
            json={"session_id": "session-2", "message": "Test"},
            headers={"X-Waywarden-Operator": "incoming-like"},
        )

        assert response.status_code in (200, 202)
        body = response.json()
        assert "run_id" in body

        # Verify event was persisted with correct type
        mock_repo.append.assert_called_once()
        call_args = mock_repo.append.call_args
        event = call_args[0][0]
        assert event.type == "run.created"
        assert event.payload.get("phase") is None  # run.created has no phase
