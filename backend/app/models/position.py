import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PositionStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    status: Mapped[PositionStatus] = mapped_column(
        Enum(PositionStatus, name="position_status"),
        default=PositionStatus.OPEN,
        nullable=False,
    )
    entry_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    invested_quote_amount: Mapped[float] = mapped_column(Float, nullable=False)
    stop_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    take_profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    exit_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    received_quote_amount: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    realized_pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    realized_pnl_percent: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    close_reason: Mapped[str | None] = mapped_column(String(30), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
