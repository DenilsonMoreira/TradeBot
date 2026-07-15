from datetime import datetime

from pydantic import BaseModel, Field


class SoakStartRequest(BaseModel):
    confirmation: str
    duration_hours: int = Field(default=168, ge=24, le=336)


class SoakCampaignResponse(BaseModel):
    id: int
    status: str
    budget_brl: float
    reference_brl_per_usdt: float
    budget_quote: float
    max_quote_per_trade: float
    max_loss_quote: float
    duration_hours: int
    symbols: list[str]
    started_at: datetime
    ends_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class SoakStatusResponse(BaseModel):
    campaign: SoakCampaignResponse | None
    metrics: dict | None

