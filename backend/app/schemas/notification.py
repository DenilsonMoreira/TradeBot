from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: int
    severity: str
    category: str
    title: str
    message: str
    resource_id: str | None
    read_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MarkAllReadResponse(BaseModel):
    updated: int
