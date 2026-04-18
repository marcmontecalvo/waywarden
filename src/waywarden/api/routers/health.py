from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from waywarden import __version__
from waywarden.api.schemas.common import StatusResponse
from waywarden.config import AppConfig, get_request_app_config

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=StatusResponse, response_model_exclude_none=True)
async def healthz(
    config: Annotated[AppConfig, Depends(get_request_app_config)],
) -> StatusResponse:
    return StatusResponse(
        status="ok",
        app="waywarden",
        version=__version__,
        commit_sha=config.commit_sha if config.expose_commit_sha else None,
    )


@router.get("/readyz", response_model=StatusResponse, response_model_exclude_none=True)
async def readyz() -> JSONResponse:
    # Fail closed until real dependency checks exist so readiness never lies.
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=StatusResponse(
            status="not_ready",
            app="waywarden",
            version=__version__,
        ).model_dump(exclude_none=True),
    )
