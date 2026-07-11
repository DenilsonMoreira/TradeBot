from unittest.mock import Mock, patch

from app.workers import indicator_worker


def test_worker_continues_after_market_failure() -> None:
    service = Mock()
    service.calculate_and_persist.side_effect = [
        RuntimeError("temporary failure"),
        [],
    ]
    with (
        patch.object(indicator_worker.settings, "candle_symbols", "BTCUSDT,ETHUSDT"),
        patch.object(indicator_worker.settings, "candle_intervals", "15m"),
        patch.object(indicator_worker, "SessionLocal") as session_factory,
        patch.object(indicator_worker, "IndicatorService", return_value=service),
    ):
        session_factory.return_value.__enter__.return_value = Mock()
        indicator_worker.run_cycle()

    assert service.calculate_and_persist.call_count == 2
    service.calculate_and_persist.assert_any_call("ETHUSDT", "15m")
