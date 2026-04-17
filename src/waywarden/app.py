from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from waywarden.settings import Settings, get_settings


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


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        lifespan=lifespan,
    )
    register_routers(app)
    app.state.settings = app_settings
    return app
