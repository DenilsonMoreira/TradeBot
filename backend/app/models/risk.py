from datetime import datetime

from sqlalchemy import DateTime, Float, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TradingRiskSettings(Base):
    __tablename__ = "trading_risk_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    auto_entry_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    max_quote_amount_per_trade: Mapped[float] = mapped_column(
        Float, default=20.0, nullable=False
    )
    max_daily_loss: Mapped[float] = mapped_column(
        Float, default=40.0, nullable=False
    )
    max_open_positions: Mapped[int] = mapped_column(default=1, nullable=False)
    cooldown_minutes: Mapped[int] = mapped_column(default=30, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
