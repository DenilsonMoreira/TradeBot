import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BotMode(str, enum.Enum):
    OFF = "OFF"
    MONITOR = "MONITOR"
    TESTNET_TRADING = "TESTNET_TRADING"


class BotStatus(Base):
    __tablename__ = "bot_status"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    mode: Mapped[BotMode] = mapped_column(
        Enum(BotMode, name="bot_mode"),
        default=BotMode.OFF,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
