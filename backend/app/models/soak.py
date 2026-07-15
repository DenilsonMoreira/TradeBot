from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Float, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TestnetSoakCampaign(Base):
    __tablename__ = "testnet_soak_campaigns"
    __table_args__ = (
        CheckConstraint(
            "status IN ('RUNNING', 'COMPLETED', 'CANCELED', 'FAILED')",
            name="ck_testnet_soak_campaigns_status",
        ),
        Index(
            "uq_testnet_soak_campaigns_one_running",
            "status",
            unique=True,
            postgresql_where=text("status = 'RUNNING'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="RUNNING")
    budget_brl: Mapped[float] = mapped_column(Float, nullable=False)
    reference_brl_per_usdt: Mapped[float] = mapped_column(Float, nullable=False)
    budget_quote: Mapped[float] = mapped_column(Float, nullable=False)
    max_quote_per_trade: Mapped[float] = mapped_column(Float, nullable=False)
    max_loss_quote: Mapped[float] = mapped_column(Float, nullable=False)
    duration_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    symbols: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    baseline_candle_counts: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

