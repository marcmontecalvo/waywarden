from typing import Annotated

from fastapi import APIRouter, Depends

from waywarden.api.schemas.common import StatusResponse
from waywarden.config import AppConfig, get_request_app_config

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=StatusResponse)
async def healthz(
    _config: Annotated[AppConfig, Depends(get_request_app_config)],
) -> StatusResponse:
    return StatusResponse(status="ok")
