from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request, Response

from waywarden import __version__
from waywarden.api.routers import health, run_events
from waywarden.config import AppConfig, get_app_config
from waywarden.logging import (
    build_request_log_context,
    configure_logging,
    get_logger,
    request_log_context,
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Startup and shutdown hooks will be filled in by later milestone issues.
    yield


def register_routers(app: FastAPI) -> None:
    app.include_router(health.router)
    app.include_router(run_events.router)


def register_middleware(app: FastAPI) -> None:
    logger = get_logger("waywarden.http")

    @app.middleware("http")
    async def bind_request_context(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        context = build_request_log_context(request.headers.get("X-Request-ID"))
        started_at = perf_counter()

        with request_log_context(context):
            logger.info(
                "request.started",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                },
            )
            response = await call_next(request)
            response.headers["X-Request-ID"] = context.request_id
            duration_ms = round((perf_counter() - started_at) * 1000, 3)
            logger.info(
                "request.completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            return response


def create_app(settings: AppConfig | None = None) -> FastAPI:
    app_settings = settings or get_app_config()
    configure_logging(level=app_settings.log_level)
    app = FastAPI(
        title="Waywarden",
        version=__version__,
        lifespan=lifespan,
    )
    app.state.settings = app_settings
    register_middleware(app)
    register_routers(app)
    return app
