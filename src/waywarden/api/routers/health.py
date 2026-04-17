from fastapi import APIRouter

from waywarden.api.schemas.common import StatusResponse

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=StatusResponse)
async def healthz() -> StatusResponse:
    return StatusResponse(status="ok")
