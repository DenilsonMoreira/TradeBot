from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models.candle import Candle
from app.models.indicator import Indicator


def make_candle() -> Candle:
    open_time = datetime(2026, 7, 10, tzinfo=UTC)
    return Candle(
        symbol="BTCUSDT",
        interval="15m",
        open_time=open_time,
        close_time=open_time + timedelta(minutes=15) - timedelta(milliseconds=1),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("105"),
        volume=Decimal("12.5"),
        quote_volume=Decimal("1300"),
        trades=42,
        taker_buy_volume=Decimal("7"),
        taker_buy_quote=Decimal("730"),
        is_closed=True,
    )


def test_indicator_references_candle_and_rejects_duplicate() -> None:
    with SessionLocal() as session:
        session.execute(delete(Indicator))
        session.execute(delete(Candle))
        candle = make_candle()
        session.add(candle)
        session.flush()
        session.add(
            Indicator(
                candle_id=candle.id,
                name="RSI",
                config_version="rsi-14-v1",
                parameters={"period": 14},
                value=Decimal("52.123456789"),
            )
        )
        session.commit()

        session.add(
            Indicator(
                candle_id=candle.id,
                name="RSI",
                config_version="rsi-14-v1",
                parameters={"period": 14},
                value=Decimal("53"),
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
