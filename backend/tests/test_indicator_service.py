from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock

from app.models.candle import Candle
from app.services.indicator_service import INDICATOR_NAMES, IndicatorService


def make_candles(count: int = 40) -> list[Candle]:
    start = datetime(2026, 7, 1, tzinfo=UTC)
    candles = []
    for index in range(count):
        price = Decimal(100 + index)
        candle = Candle(
            symbol="BTCUSDT",
            interval="15m",
            open_time=start + timedelta(minutes=15 * index),
            close_time=start + timedelta(minutes=15 * (index + 1)),
            open=price,
            high=price + 1,
            low=price - 1,
            close=price,
            volume=Decimal(10),
            quote_volume=Decimal(1000),
            trades=10,
            taker_buy_volume=Decimal(5),
            taker_buy_quote=Decimal(500),
            is_closed=True,
        )
        candle.id = index + 1
        candles.append(candle)
    return candles


def test_service_calculates_and_persists_versioned_indicators() -> None:
    candle_repository = Mock()
    candle_repository.get_history.return_value = list(reversed(make_candles()))
    indicator_repository = Mock()
    indicator_repository.session = Mock()
    indicator_repository.get_existing_keys.return_value = set()
    indicator_repository.upsert_many.side_effect = lambda items: items
    service = IndicatorService(
        candle_repository,
        indicator_repository,
        history_limit=1000,
    )

    result = service.calculate_and_persist("btcusdt", "15m")

    assert len(result) == 266
    assert {item.name for item in result} == INDICATOR_NAMES
    assert all(item.config_version == "technical-v1-h1000" for item in result)
    candle_repository.get_history.assert_called_once_with(
        "btcusdt",
        "15m",
        limit=1000,
        closed_only=True,
    )
    indicator_repository.session.commit.assert_called_once_with()


def test_service_skips_recalculation_when_latest_is_complete() -> None:
    candles = make_candles()
    candle_repository = Mock()
    candle_repository.get_history.return_value = list(reversed(candles))
    indicator_repository = Mock()
    indicator_repository.session = Mock()
    indicator_repository.get_existing_keys.return_value = {
        (candles[-1].id, name) for name in INDICATOR_NAMES
    }
    service = IndicatorService(candle_repository, indicator_repository)

    assert service.calculate_and_persist("BTCUSDT", "15m") == []
    indicator_repository.upsert_many.assert_not_called()
    indicator_repository.session.commit.assert_not_called()


def test_service_requires_reproducible_minimum_history_window() -> None:
    try:
        IndicatorService(Mock(), Mock(), history_limit=49)
    except ValueError as error:
        assert "mínimo" in str(error)
    else:
        raise AssertionError("history_limit inválido deveria falhar")
