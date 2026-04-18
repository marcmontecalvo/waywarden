from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from waywarden.api.schemas.common import PlaceholderResponse

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get(
    "/health",
    response_model=PlaceholderResponse,
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
)
async def memory_health() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=PlaceholderResponse(
            status="not_ready",
            feature="memory",
            message=(
                "Memory provider wiring is still placeholder-only; no live provider health "
                "is available."
            ),
        ).model_dump(),
    )
