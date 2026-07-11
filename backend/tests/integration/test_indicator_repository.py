from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import delete

from app.database import SessionLocal
from app.models.candle import Candle
from app.models.indicator import Indicator
from app.repositories.indicator_repository import IndicatorRepository


def make_candle(open_time: datetime) -> Candle:
    return Candle(
        symbol="BTCUSDT",
        interval="15m",
        open_time=open_time,
        close_time=open_time + timedelta(minutes=15),
        open=Decimal(100),
        high=Decimal(110),
        low=Decimal(90),
        close=Decimal(105),
        volume=Decimal(10),
        quote_volume=Decimal(1000),
        trades=10,
        taker_buy_volume=Decimal(5),
        taker_buy_quote=Decimal(500),
        is_closed=True,
    )


def test_repository_upserts_and_queries_by_market_context() -> None:
    with SessionLocal() as session:
        session.execute(delete(Indicator))
        session.execute(delete(Candle))
        candle = make_candle(datetime(2026, 7, 10, tzinfo=UTC))
        session.add(candle)
        session.flush()
        repository = IndicatorRepository(session)
        repository.upsert_many(
            [
                Indicator(
                    candle_id=candle.id,
                    name="RSI_14",
                    config_version="technical-v1-h1000",
                    parameters={"period": 14},
                    value=Decimal("51.5"),
                )
            ]
        )
        repository.upsert_many(
            [
                Indicator(
                    candle_id=candle.id,
                    name="RSI_14",
                    config_version="technical-v1-h1000",
                    parameters={"period": 14},
                    value=Decimal("52.5"),
                )
            ]
        )
        session.commit()

        history = repository.get_history(
            "btcusdt",
            "15m",
            name="rsi_14",
        )
        keys = repository.get_existing_keys(
            [candle.id],
            "technical-v1-h1000",
        )

        assert len(history) == 1
        assert history[0].value == Decimal("52.5")
        assert keys == {(candle.id, "RSI_14")}
