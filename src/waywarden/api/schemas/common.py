from pydantic import BaseModel


class StatusResponse(BaseModel):
    status: str
    app: str
    version: str
    commit_sha: str | None = None
