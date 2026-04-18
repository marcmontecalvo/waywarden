from pydantic import BaseModel


class StatusResponse(BaseModel):
    status: str
    app: str
    version: str
    commit_sha: str | None = None


class PlaceholderResponse(BaseModel):
    status: str
    feature: str
    placeholder: bool = True
    message: str
