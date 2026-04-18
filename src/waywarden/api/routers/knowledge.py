from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from waywarden.api.schemas.common import PlaceholderResponse

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get(
    "/health",
    response_model=PlaceholderResponse,
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
)
async def knowledge_health() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=PlaceholderResponse(
            status="not_ready",
            feature="knowledge",
            message=(
                "Knowledge provider wiring is still placeholder-only; no live provider "
                "health is available."
            ),
        ).model_dump(),
    )
