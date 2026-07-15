from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.ai.datasets.builder import build_rows, validate_candle_continuity
from app.ai.trainer import train_candidates
from app.backtest.engine import BacktestConfig, run_ema_cross_backtest
from app.models.candle import Candle


def candles(count=120):
    start = datetime(2026, 1, 1, tzinfo=UTC)
    result = []
    for index in range(count):
        wave = Decimal(index % 30 if (index // 30) % 2 == 0 else 30 - index % 30)
        price = Decimal(100) + wave
        item = Candle(symbol="BTCUSDT", interval="15m", open_time=start + timedelta(minutes=15 * index), close_time=start + timedelta(minutes=15 * (index + 1)), open=price, high=price + 2, low=price - 2, close=price + Decimal("0.5"), volume=Decimal(100 + index), quote_volume=Decimal(10000), trades=100, taker_buy_volume=Decimal(50), taker_buy_quote=Decimal(5000), is_closed=True)
        item.id = index + 1
        result.append(item)
    return result


def test_backtest_is_deterministic_and_charges_costs():
    data = candles()
    config = BacktestConfig()
    first = run_ema_cross_backtest(data, config)
    second = run_ema_cross_backtest(data, config)
    assert first == second
    assert first.metrics["trade_count"] > 0
    assert first.final_capital > 0


def test_dataset_is_temporal_and_has_no_future_last_row():
    data = candles()
    rows = build_rows(data, horizon=1)
    assert rows
    assert rows == sorted(rows, key=lambda row: row["open_time"])
    assert rows[-1]["candle_id"] < data[-1].id
    assert all("label" in row and "future_return" in row for row in rows)


def test_dataset_rejects_large_price_discontinuity():
    data = candles()
    data[60].close = Decimal("1")

    with pytest.raises(ValueError, match="descontinuidade"):
        validate_candle_continuity(data)


def test_training_compares_baseline_and_models(tmp_path):
    rows = build_rows(candles(180), horizon=1)
    results = train_candidates(rows, list(rows[0]["features"]), int(len(rows) * 0.8), str(tmp_path), "test-dataset")
    assert {name for name, _, _ in results} == {
        "baseline",
        "logistic_regression",
        "random_forest",
        "xgboost",
        "lightgbm",
        "catboost",
    }
    assert all("strategy_return" in metrics for _, metrics, _ in results)
    assert all((tmp_path / f"test-dataset-{name}.joblib").exists() for name, _, _ in results)


def test_training_can_select_only_missing_algorithms(tmp_path):
    rows = build_rows(candles(180), horizon=1)
    results = train_candidates(
        rows,
        list(rows[0]["features"]),
        int(len(rows) * 0.8),
        str(tmp_path),
        "incremental",
        algorithms={"xgboost", "lightgbm", "catboost"},
    )
    assert {name for name, _, _ in results} == {
        "xgboost",
        "lightgbm",
        "catboost",
    }
