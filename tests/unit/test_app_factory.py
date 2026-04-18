from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from waywarden.app import create_app
from waywarden.config import AppConfig, get_request_app_config


def test_create_app_uses_injected_settings() -> None:
    settings = AppConfig(host="127.0.0.1", port=9001, commit_sha="abc123")

    app = create_app(settings)

    assert isinstance(app, FastAPI)
    assert app.title == "Waywarden"
    assert app.state.settings is settings


def test_app_config_available_via_dependency_injection() -> None:
    settings = AppConfig(host="127.0.0.1", port=9001, commit_sha="abc123")
    app = create_app(settings)

    @app.get("/_test-config")
    async def read_config(
        config: Annotated[AppConfig, Depends(get_request_app_config)],
    ) -> dict[str, str | int]:
        return {"host": config.host, "port": config.port}

    client = TestClient(app)
    response = client.get("/_test-config")

    assert response.status_code == 200
    assert response.json() == {"host": "127.0.0.1", "port": 9001}
