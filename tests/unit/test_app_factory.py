from fastapi import FastAPI

from waywarden.app import create_app
from waywarden.settings import Settings


def test_create_app_uses_injected_settings() -> None:
    settings = Settings(app_name="Waywarden Test", app_version="9.9.9")

    app = create_app(settings)

    assert isinstance(app, FastAPI)
    assert app.title == "Waywarden Test"
    assert app.version == "9.9.9"
    assert app.state.settings is settings
