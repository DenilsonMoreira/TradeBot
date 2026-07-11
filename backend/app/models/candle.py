from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Candle(Base):
    __tablename__ = "candles"
    __table_args__ = (
        UniqueConstraint(
            "symbol",
            "interval",
            "open_time",
            name="uq_candles_symbol_interval_open_time",
        ),
        Index(
            "ix_candles_symbol_interval_open_time",
            "symbol",
            "interval",
            "open_time",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    interval: Mapped[str] = mapped_column(String(10), nullable=False)
    open_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    close_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    open: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    quote_volume: Mapped[Decimal] = mapped_column(
        Numeric(38, 18), nullable=False
    )
    trades: Mapped[int] = mapped_column(BigInteger, nullable=False)
    taker_buy_volume: Mapped[Decimal] = mapped_column(
        Numeric(38, 18), nullable=False
    )
    taker_buy_quote: Mapped[Decimal] = mapped_column(
        Numeric(38, 18), nullable=False
    )
    is_closed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
