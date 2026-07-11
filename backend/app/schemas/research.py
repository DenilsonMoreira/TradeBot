from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class BacktestRequest(BaseModel):
    symbol: str = "BTCUSDT"
    interval: str = "15m"
    limit: int = Field(default=1000, ge=30, le=10000)
    initial_capital: Decimal = Field(default=Decimal("1000"), gt=0)
    fee_rate: Decimal = Field(default=Decimal("0.001"), ge=0, le=Decimal("0.05"))
    slippage_rate: Decimal = Field(default=Decimal("0.0005"), ge=0, le=Decimal("0.05"))


class BacktestResponse(BaseModel):
    id: int
    symbol: str
    interval: str
    strategy: str
    initial_capital: Decimal
    final_capital: Decimal
    metrics: dict[str, Any]
    trades: list[dict[str, Any]]
    created_at: datetime
    model_config = {"from_attributes": True}


class DatasetRequest(BaseModel):
    symbol: str = "BTCUSDT"
    interval: str = "15m"
    limit: int = Field(default=1000, ge=50, le=10000)
    horizon: int = Field(default=1, ge=1, le=20)
    train_ratio: float = Field(default=0.8, ge=0.5, lt=1)


class DatasetResponse(BaseModel):
    id: int
    symbol: str
    interval: str
    version: str
    feature_names: list[str]
    train_size: int
    test_size: int
    metadata_json: dict[str, Any]
    created_at: datetime
    model_config = {"from_attributes": True}


class TrainingRequest(BaseModel):
    dataset_id: int = Field(gt=0)


class ModelResponse(BaseModel):
    id: int
    dataset_id: int
    algorithm: str
    version: str
    metrics: dict[str, Any]
    artifact_path: str
    created_at: datetime
    model_config = {"from_attributes": True}
