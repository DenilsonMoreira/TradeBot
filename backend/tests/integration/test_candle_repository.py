from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import delete

from app.database import SessionLocal
from app.models.candle import Candle
from app.repositories.candle_repository import CandleRepository


@pytest.fixture
def repository():
    with SessionLocal() as session:
        session.execute(delete(Candle))
        session.commit()
        yield CandleRepository(session)
        session.rollback()
        session.execute(delete(Candle))
        session.commit()


def candle_at(open_time: datetime, **overrides) -> Candle:
    values = {
        "symbol": "BTCUSDT",
        "interval": "1m",
        "open_time": open_time,
        "close_time": open_time + timedelta(seconds=59),
        "open": Decimal("100.000000000000"),
        "high": Decimal("110.000000000000"),
        "low": Decimal("90.000000000000"),
        "close": Decimal("105.000000000000"),
        "volume": Decimal("12.500000000000000000"),
        "quote_volume": Decimal("1300.000000000000000000"),
        "trades": 42,
        "taker_buy_volume": Decimal("7.000000000000000000"),
        "taker_buy_quote": Decimal("730.000000000000000000"),
        "is_closed": True,
    }
    values.update(overrides)
    return Candle(**values)


def test_save_many_and_history_queries(repository: CandleRepository) -> None:
    start = datetime(2026, 7, 10, tzinfo=UTC)
    repository.save_many(
        [
            candle_at(start),
            candle_at(start + timedelta(minutes=1)),
            candle_at(start + timedelta(minutes=2), is_closed=False),
        ]
    )

    history = repository.get_history("btcusdt", "1m")

    assert [item.open_time for item in history] == [
        start + timedelta(minutes=1),
        start,
    ]
    assert repository.get_latest("btcusdt", "1m").open_time == (
        start + timedelta(minutes=2)
    )
    assert repository.get_last_open_time("BTCUSDT", "1m") == (
        start + timedelta(minutes=2)
    )
    assert repository.exists("btcusdt", "1m", start) is True
    assert repository.count_after("BTCUSDT", "1m", start) == 1
    assert repository.count_after(
        "BTCUSDT",
        "1m",
        start,
        closed_only=False,
    ) == 2


def test_upsert_many_is_idempotent_and_updates_open_candle(
    repository: CandleRepository,
) -> None:
    open_time = datetime(2026, 7, 10, tzinfo=UTC)
    repository.upsert_many([candle_at(open_time, is_closed=False)])
    repository.upsert_many(
        [
            candle_at(
                open_time,
                close=Decimal("108.000000000000"),
                trades=50,
                is_closed=True,
            )
        ]
    )

    history = repository.get_history("BTCUSDT", "1m")

    assert len(history) == 1
    assert history[0].close == Decimal("108.000000000000")
    assert history[0].trades == 50
    assert history[0].is_closed is True


def test_get_history_validates_pagination(repository: CandleRepository) -> None:
    with pytest.raises(ValueError, match="limit"):
        repository.get_history("BTCUSDT", "1m", limit=0)

    with pytest.raises(ValueError, match="offset"):
        repository.get_history("BTCUSDT", "1m", offset=-1)
