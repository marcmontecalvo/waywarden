from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from waywarden.api.schemas.common import PlaceholderResponse

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=PlaceholderResponse, status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def list_approvals() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content=PlaceholderResponse(
            status="not_implemented",
            feature="approvals",
            message=(
                "Approval listing is a placeholder until approval state storage is implemented."
            ),
        ).model_dump(),
    )
