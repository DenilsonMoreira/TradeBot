import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.candle_service import CandleService


NOW = datetime(2026, 7, 10, 0, 2, tzinfo=UTC)
OPEN_TIME_MS = 1_783_641_600_000
CLOSE_TIME_MS = OPEN_TIME_MS + 59_999


def payload(
    *,
    open_time: int = OPEN_TIME_MS,
    close_time: int = CLOSE_TIME_MS,
    close: str = "105.25",
) -> list:
    return [
        open_time,
        "100.10",
        "110.20",
        "90.30",
        close,
        "12.50",
        close_time,
        "1300.75",
        42,
        "7.25",
        "730.55",
        "0",
    ]


def service_with(repository=None, client=None) -> CandleService:
    repository = repository or Mock()
    repository.session = getattr(repository, "session", Mock())
    return CandleService(
        repository,
        client or AsyncMock(),
        now=lambda: NOW,
    )


def test_normalize_candle_uses_decimal_utc_and_closed_state() -> None:
    candle = service_with().normalize_candle("btcusdt", "1m", payload())

    assert candle.symbol == "BTCUSDT"
    assert candle.open == Decimal("100.10")
    assert candle.close == Decimal("105.25")
    assert candle.open_time.tzinfo is UTC
    assert candle.is_closed is True


def test_normalize_candle_rejects_incomplete_payload() -> None:
    with pytest.raises(ValueError, match="incompleto"):
        service_with().normalize_candle("BTCUSDT", "1m", [1, 2])


def test_sync_history_fetches_normalizes_and_commits() -> None:
    repository = Mock()
    repository.session = Mock()
    repository.upsert_many.side_effect = lambda candles: candles
    client = AsyncMock()
    client.get_candles.return_value = [payload()]
    service = service_with(repository, client)

    result = asyncio.run(service.sync_history("btcusdt", "1m", limit=100))

    client.get_candles.assert_awaited_once_with("BTCUSDT", "1m", 100)
    repository.session.commit.assert_called_once_with()
    assert len(result) == 1


def test_incremental_advances_after_closed_candle() -> None:
    repository = Mock()
    repository.session = Mock()
    repository.get_latest.return_value = Mock(
        open_time=datetime.fromtimestamp(OPEN_TIME_MS / 1000, tz=UTC),
        is_closed=True,
    )
    repository.upsert_many.return_value = []
    client = AsyncMock()
    client.get_candles.return_value = []
    service = service_with(repository, client)

    asyncio.run(service.sync_incremental("BTCUSDT", "1m", limit=10))

    client.get_candles.assert_awaited_once_with(
        "BTCUSDT", "1m", 10, start_time=OPEN_TIME_MS + 1
    )


def test_incremental_refetches_last_open_candle() -> None:
    repository = Mock()
    repository.session = Mock()
    repository.get_latest.return_value = Mock(
        open_time=datetime.fromtimestamp(OPEN_TIME_MS / 1000, tz=UTC),
        is_closed=False,
    )
    client = AsyncMock()
    client.get_candles.return_value = []
    service = service_with(repository, client)

    asyncio.run(service.sync_incremental("BTCUSDT", "1m"))

    client.get_candles.assert_awaited_once_with(
        "BTCUSDT", "1m", 500, start_time=OPEN_TIME_MS
    )


def test_historical_sync_fetches_before_first_candle() -> None:
    repository = Mock()
    repository.session = Mock()
    repository.get_first_open_time.return_value = datetime.fromtimestamp(
        OPEN_TIME_MS / 1000,
        tz=UTC,
    )
    repository.upsert_many.return_value = []
    client = AsyncMock()
    client.get_candles.return_value = []
    service = service_with(repository, client)

    asyncio.run(service.sync_historical_before("btcusdt", "1m", limit=1000))

    client.get_candles.assert_awaited_once_with(
        "BTCUSDT", "1m", 1000, end_time=OPEN_TIME_MS - 1
    )


def test_historical_sync_bootstraps_empty_market() -> None:
    repository = Mock()
    repository.session = Mock()
    repository.get_first_open_time.return_value = None
    repository.upsert_many.side_effect = lambda candles: candles
    client = AsyncMock()
    client.get_candles.return_value = [payload()]
    service = service_with(repository, client)

    result = asyncio.run(
        service.sync_historical_before("BTCUSDT", "1m", limit=100)
    )

    client.get_candles.assert_awaited_once_with("BTCUSDT", "1m", 100)
    assert len(result) == 1


def test_persistence_failure_rolls_back() -> None:
    repository = Mock()
    repository.session = Mock()
    repository.upsert_many.side_effect = RuntimeError("database unavailable")
    client = AsyncMock()
    client.get_candles.return_value = [payload()]
    service = service_with(repository, client)

    with pytest.raises(RuntimeError, match="database unavailable"):
        asyncio.run(service.sync_history("BTCUSDT", "1m"))

    repository.session.rollback.assert_called_once_with()
    repository.session.commit.assert_not_called()
