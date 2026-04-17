from pydantic import BaseModel


class TaskCreateRequest(BaseModel):
    title: str
    description: str | None = None


class TaskResponse(BaseModel):
    id: str
    title: str
    status: str
