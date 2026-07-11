from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator


class IndicatorResponse(BaseModel):
    id: int
    candle_id: int
    name: str
    config_version: str
    parameters: dict[str, Any]
    value: Decimal
    created_at: datetime
    model_config = {"from_attributes": True}


class IndicatorCalculateRequest(BaseModel):
    symbol: str = Field(min_length=5, max_length=20)
    interval: str = Field(min_length=2, max_length=10)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()


class IndicatorCalculateResponse(BaseModel):
    symbol: str
    interval: str
    config_version: str
    persisted: int
