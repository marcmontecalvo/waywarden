from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from waywarden.api.schemas.chat import ChatRequest
from waywarden.api.schemas.common import PlaceholderResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=PlaceholderResponse, status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def chat(_request: ChatRequest) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content=PlaceholderResponse(
            status="not_implemented",
            feature="chat",
            message=(
                "Chat orchestration is placeholder-only in this slice; no persisted sessions, "
                "provider execution, or model routing is active yet."
            ),
        ).model_dump(),
    )
