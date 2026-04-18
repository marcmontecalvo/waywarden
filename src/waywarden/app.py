from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from waywarden import __version__
from waywarden.config import AppConfig, get_app_config


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Startup and shutdown hooks will be filled in by later milestone issues.
    yield


def register_routers(app: FastAPI) -> None:
    from waywarden.api.routers import (
        approvals,
        backups,
        chat,
        health,
        knowledge,
        memory,
        skills,
        tasks,
    )

    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(tasks.router)
    app.include_router(approvals.router)
    app.include_router(skills.router)
    app.include_router(memory.router)
    app.include_router(knowledge.router)
    app.include_router(backups.router)


def create_app(settings: AppConfig | None = None) -> FastAPI:
    app_settings = settings or get_app_config()
    app = FastAPI(
        title="Waywarden",
        version=__version__,
        lifespan=lifespan,
    )
    register_routers(app)
    app.state.settings = app_settings
    return app
