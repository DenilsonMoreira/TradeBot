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

class ManualBuyRequest(BaseModel):
    confirmation: str
    quote_amount: float = Field(default=6.0, ge=6.0, le=20.0)


class OrderResponse(BaseModel):
    id: UUID
    symbol: str
    side: str
    order_type: str
    status: str
    exchange_order_id: str | None
    requested_quote_amount: float
    executed_quantity: float | None
    executed_price: float | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

class ManualSellRequest(BaseModel):
    confirmation: str


class PositionResponse(BaseModel):
    id: UUID
    symbol: str
    status: str
    quantity: float
    entry_price: float
    invested_quote_amount: float
    stop_loss: float | None
    take_profit: float | None
    exit_price: float | None
    received_quote_amount: float | None
    realized_pnl: float | None
    realized_pnl_percent: float | None
    close_reason: str | None
    opened_at: datetime
    closed_at: datetime | None
    

    model_config = {"from_attributes": True}

class TradingRiskSettingsUpdate(BaseModel):
    auto_entry_enabled: bool
    max_quote_amount_per_trade: float = Field(
        ge=6.0,
        le=20.0,
    )
    max_daily_loss: float = Field(
        ge=1.0,
        le=500.0,
    )
    max_open_positions: int = Field(
        ge=1,
        le=1,
    )
    cooldown_minutes: int = Field(
        ge=1,
        le=1440,
    )
    confirmation: str | None = None


class TradingRiskSettingsResponse(BaseModel):
    auto_entry_enabled: bool
    max_quote_amount_per_trade: float
    max_daily_loss: float
    max_open_positions: int
    cooldown_minutes: int
    updated_at: datetime

    model_config = {"from_attributes": True}
