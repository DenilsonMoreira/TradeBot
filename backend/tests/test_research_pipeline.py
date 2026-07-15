from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.ai.datasets.builder import FEATURE_NAMES, build_rows, validate_candle_continuity
from app.ai.evaluator import evaluate_predictions
from app.ai.trainer import select_threshold, train_candidates
from app.ai.walk_forward import (
    aggregate_walk_forward_metrics,
    build_walk_forward_splits,
)
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
    assert set(rows[0]["features"]) == set(FEATURE_NAMES)


def test_dataset_rejects_large_price_discontinuity():
    data = candles()
    data[60].close = Decimal("1")

    with pytest.raises(ValueError, match="descontinuidade"):
        validate_candle_continuity(data)


def test_financial_evaluation_compounds_returns_and_costs():
    metrics = evaluate_predictions(
        [1, 0, 1],
        [1, 0, 1],
        [0.8, 0.2, 0.7],
        [0.02, -0.01, 0.03],
        cost_rate=0.001,
    )

    expected = ((1 - 0.001) ** 2 * 1.02) * (
        (1 - 0.001) ** 2 * 1.03
    ) - 1
    assert metrics["strategy_return"] == pytest.approx(expected)
    assert metrics["buy_and_hold_return"] == pytest.approx(
        1.02 * 0.99 * 1.03 - 1
    )
    assert metrics["trade_count"] == 2


def test_threshold_is_selected_on_validation_financial_return():
    threshold, metrics = select_threshold(
        [1, 0, 1, 0, 1, 0],
        [0.85, 0.75, 0.8, 0.7, 0.9, 0.55],
        [0.02, -0.03, 0.01, -0.02, 0.03, -0.01],
        holding_period=1,
        cost_rate=0.001,
        min_trades=2,
    )

    assert threshold >= 0.8
    assert metrics["strategy_return"] > 0


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
    assert all(metrics["walk_forward_folds"] == 3 for _, metrics, _ in results)
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


def test_walk_forward_splits_are_expanding_and_non_overlapping():
    splits = build_walk_forward_splits(100)

    assert splits == [(50, 66), (66, 82), (82, 100)]
    assert all(first[1] == second[0] for first, second in zip(splits, splits[1:]))


def test_walk_forward_metrics_compound_sequential_fold_returns():
    metrics = aggregate_walk_forward_metrics([
        {"strategy_return": 0.1, "f1": 0.6, "roc_auc": 0.7, "trade_count": 3},
        {"strategy_return": -0.05, "f1": 0.4, "roc_auc": None, "trade_count": 2},
        {"strategy_return": 0.02, "f1": 0.5, "roc_auc": 0.6, "trade_count": 4},
    ])

    assert metrics["walk_forward_return"] == pytest.approx(1.1 * 0.95 * 1.02 - 1)
    assert metrics["walk_forward_profitable_folds"] == 2
    assert metrics["walk_forward_trade_count"] == 9
    assert metrics["walk_forward_worst_fold_return"] == -0.05
