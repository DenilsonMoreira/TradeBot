from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        UniqueConstraint("model_id", "candle_id", name="uq_predictions_model_candle"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    model_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("trained_models.id", ondelete="CASCADE"), nullable=False)
    dataset_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    candle_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("candles.id", ondelete="CASCADE"), nullable=False)
    probability: Mapped[Decimal] = mapped_column(Numeric(20, 18), nullable=False)
    signal: Mapped[str] = mapped_column(String(16), nullable=False)
    features: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
