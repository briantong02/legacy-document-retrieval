from datetime import datetime

from pydantic import BaseModel


class CurrentUserResponse(BaseModel):
    username: str
    displayName: str
    email: str | None = None
    groups: list[str]


class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: datetime
