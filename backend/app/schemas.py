from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import BotMode


class BotStatusResponse(BaseModel):
    mode: BotMode
    updated_at: datetime


class BotModeUpdate(BaseModel):
    mode: BotMode
    confirmation: str | None = Field(
        default=None,
        description="Obrigatório apenas para TESTNET_TRADING",
    )


class SignalCreate(BaseModel):
    symbol: str = Field(examples=["BTCUSDT"])
    timeframe: str = Field(default="15m")
    signal_type: str = Field(examples=["BUY", "SELL", "HOLD"])
    price: float = Field(gt=0)
    confidence: float | None = Field(default=None, ge=0, le=100)
    strategy_name: str = Field(default="EMA_RSI_V1")
    details: str | None = None


class SignalResponse(SignalCreate):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}