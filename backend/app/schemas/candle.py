from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class CandleResponse(BaseModel):
    id: int
    symbol: str
    interval: str
    open_time: datetime
    close_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    quote_volume: Decimal
    trades: int
    taker_buy_volume: Decimal
    taker_buy_quote: Decimal
    is_closed: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class CandleSyncRequest(BaseModel):
    symbol: str = Field(min_length=5, max_length=20, examples=["BTCUSDT"])
    interval: str = Field(min_length=2, max_length=10, examples=["15m"])
    limit: int = Field(default=500, ge=1, le=1000)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()


class CandleSyncResponse(BaseModel):
    symbol: str
    interval: str
    synchronized: int
    candles: list[CandleResponse]


class MarketConfigResponse(BaseModel):
    symbols: list[str]
    intervals: list[str]
    dashboard_refresh_seconds: int
