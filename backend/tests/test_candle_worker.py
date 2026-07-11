import asyncio
from unittest.mock import AsyncMock, Mock, patch

from app.workers import candle_worker


def test_run_cycle_continues_after_symbol_failure() -> None:
    service = Mock()
    service.sync_incremental = AsyncMock(
        side_effect=[RuntimeError("temporary failure"), []]
    )

    with (
        patch.object(candle_worker.settings, "candle_symbols", "BTCUSDT,ETHUSDT"),
        patch.object(candle_worker.settings, "candle_intervals", "15m"),
        patch.object(candle_worker, "SessionLocal") as session_factory,
        patch.object(candle_worker, "CandleService", return_value=service),
    ):
        session_factory.return_value.__enter__.return_value = Mock()
        asyncio.run(candle_worker.run_cycle())

    assert service.sync_incremental.await_count == 2
    service.sync_incremental.assert_any_await(
        "ETHUSDT",
        "15m",
        limit=candle_worker.settings.candle_sync_limit,
    )
