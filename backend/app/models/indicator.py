from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Indicator(Base):
    __tablename__ = "indicators"
    __table_args__ = (
        UniqueConstraint(
            "candle_id",
            "name",
            "config_version",
            name="uq_indicators_candle_name_config_version",
        ),
        Index(
            "ix_indicators_name_config_version",
            "name",
            "config_version",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    candle_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("candles.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    config_version: Mapped[str] = mapped_column(String(32), nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    value: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
