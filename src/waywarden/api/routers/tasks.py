from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from waywarden.api.schemas.common import PlaceholderResponse
from waywarden.api.schemas.task import TaskCreateRequest

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=PlaceholderResponse, status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def create_task(_request: TaskCreateRequest) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content=PlaceholderResponse(
            status="not_implemented",
            feature="tasks",
            message=(
                "Task creation is not wired to persistence or queues yet. "
                "The route no longer returns synthetic task IDs."
            ),
        ).model_dump(),
    )
