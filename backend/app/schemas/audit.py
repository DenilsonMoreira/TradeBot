from datetime import datetime

from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    id: int
    actor: str
    action: str
    resource: str
    resource_id: str | None
    details: dict
    created_at: datetime

    model_config = {"from_attributes": True}
