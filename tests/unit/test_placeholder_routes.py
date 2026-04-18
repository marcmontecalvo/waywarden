from fastapi.testclient import TestClient

from waywarden.app import create_app
from waywarden.config import AppConfig
from waywarden.profiles.ea.skills.factory import build_ea_skill_registry


def _client() -> TestClient:
    settings = AppConfig(host="127.0.0.1", port=9001, log_level="INFO")
    return TestClient(create_app(settings))


def test_chat_route_is_explicitly_not_implemented() -> None:
    response = _client().post("/chat", json={"message": "hello"})

    assert response.status_code == 501
    assert response.json() == {
        "status": "not_implemented",
        "feature": "chat",
        "placeholder": True,
        "message": (
            "Chat orchestration is placeholder-only in this slice; no persisted sessions, "
            "provider execution, or model routing is active yet."
        ),
    }


def test_tasks_route_no_longer_returns_fake_ids() -> None:
    response = _client().post("/tasks", json={"title": "Follow up"})

    assert response.status_code == 501
    assert response.json() == {
        "status": "not_implemented",
        "feature": "tasks",
        "placeholder": True,
        "message": (
            "Task creation is not wired to persistence or queues yet. "
            "The route no longer returns synthetic task IDs."
        ),
    }


def test_approvals_route_no_longer_reports_empty_ready_state() -> None:
    response = _client().get("/approvals")

    assert response.status_code == 501
    assert response.json() == {
        "status": "not_implemented",
        "feature": "approvals",
        "placeholder": True,
        "message": "Approval listing is a placeholder until approval state storage is implemented.",
    }


def test_memory_and_knowledge_health_fail_closed() -> None:
    memory_response = _client().get("/memory/health")
    knowledge_response = _client().get("/knowledge/health")

    assert memory_response.status_code == 503
    assert memory_response.json() == {
        "status": "not_ready",
        "feature": "memory",
        "placeholder": True,
        "message": (
            "Memory provider wiring is still placeholder-only; no live provider health "
            "is available."
        ),
    }
    assert knowledge_response.status_code == 503
    assert knowledge_response.json() == {
        "status": "not_ready",
        "feature": "knowledge",
        "placeholder": True,
        "message": (
            "Knowledge provider wiring is still placeholder-only; no live provider "
            "health is available."
        ),
    }


def test_backup_route_no_longer_reports_fake_queueing() -> None:
    response = _client().post("/backups/run")

    assert response.status_code == 501
    assert response.json() == {
        "status": "not_implemented",
        "feature": "backups",
        "placeholder": True,
        "message": "Backup execution is not wired yet; this route no longer reports fake queueing.",
    }


def test_skills_route_exposes_placeholder_state_without_registry() -> None:
    response = _client().get("/skills")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "feature": "skills",
        "placeholder": True,
        "message": (
            "No skill registry is loaded in this app instance yet. "
            "Inject a profile-backed registry before treating this route as active."
        ),
    }


def test_skills_route_can_surface_static_scaffolding_when_injected() -> None:
    settings = AppConfig(host="127.0.0.1", port=9001, log_level="INFO")
    client = TestClient(create_app(settings, skill_registry=build_ea_skill_registry()))

    response = client.get("/skills")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "placeholder"
    assert body["feature"] == "skills"
    assert body["placeholder"] is True
    assert "static profile scaffolding only" in body["message"]
    assert any(item["name"] == "project_manager" for item in body["items"])
