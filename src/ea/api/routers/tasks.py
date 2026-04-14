import uuid

from fastapi import APIRouter

from ea.api.schemas.task import TaskCreateRequest, TaskResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse)
async def create_task(request: TaskCreateRequest) -> TaskResponse:
    return TaskResponse(id=str(uuid.uuid4()), title=request.title, status="open")
