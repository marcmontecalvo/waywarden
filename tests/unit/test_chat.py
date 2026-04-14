from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from ea.adapters.db.session import get_db
from ea.api.routers.chat import orchestrator
from ea.app import app
from ea.domain.services.orchestrator import OrchestratorResult


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # Override the DB dependency so tests don't need a running Postgres
    async def fake_db():
        mock_session = AsyncMock()
        yield mock_session

    app.dependency_overrides[get_db] = fake_db

    # Patch the orchestrator so tests don't call real LLM APIs
    mock_result = MagicMock(spec=OrchestratorResult)
    mock_result.reply = "Here are your open tasks."
    mock_result.skill = "project_manager"
    monkeypatch.setattr(orchestrator, "handle_message", AsyncMock(return_value=mock_result))

    yield TestClient(app)

    app.dependency_overrides.clear()


def test_chat_returns_reply(client: TestClient) -> None:
    response = client.post("/chat", json={"session_id": "test-session", "message": "What tasks do I have?"})
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "test-session"
    assert body["reply"] == "Here are your open tasks."
    assert body["skill"] == "project_manager"


def test_chat_generates_session_id_when_absent(client: TestClient) -> None:
    response = client.post("/chat", json={"message": "Hello"})
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"]  # auto-generated UUID
    assert body["reply"]
