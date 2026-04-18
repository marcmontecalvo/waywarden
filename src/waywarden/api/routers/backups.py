from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from waywarden.api.schemas.common import PlaceholderResponse

router = APIRouter(prefix="/backups", tags=["backups"])


@router.post(
    "/run",
    response_model=PlaceholderResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def run_backup() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content=PlaceholderResponse(
            status="not_implemented",
            feature="backups",
            message=(
                "Backup execution is not wired yet; this route no longer reports fake queueing."
            ),
        ).model_dump(),
    )
