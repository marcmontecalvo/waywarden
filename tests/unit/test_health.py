from fastapi.testclient import TestClient

from waywarden import __version__
from waywarden.app import create_app
from waywarden.config import AppConfig


def test_healthz_omits_commit_sha_by_default() -> None:
    settings = AppConfig(host="127.0.0.1", port=9001, commit_sha="abc123")
    client = TestClient(create_app(settings))
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": "waywarden",
        "version": __version__,
    }


def test_healthz_includes_commit_sha_when_enabled() -> None:
    settings = AppConfig(
        host="127.0.0.1",
        port=9001,
        commit_sha="abc123",
        expose_commit_sha=True,
    )
    client = TestClient(create_app(settings))
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": "waywarden",
        "version": __version__,
        "commit_sha": "abc123",
    }


def test_readyz_returns_503_until_readiness_checks_exist() -> None:
    client = TestClient(create_app())
    response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "status": "not_ready",
            "app": "waywarden",
            "version": __version__,
        }
    }
