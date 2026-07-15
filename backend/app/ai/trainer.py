from pathlib import Path

import joblib
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier

from app.ai.evaluator import evaluate_predictions
from app.ai.walk_forward import (
    aggregate_walk_forward_metrics,
    build_walk_forward_splits,
)


THRESHOLD_GRID = tuple(value / 100 for value in range(50, 91, 5))


def build_models(y_train) -> dict:
    positive_count = sum(y_train)
    negative_count = len(y_train) - positive_count
    scale_pos_weight = negative_count / max(positive_count, 1)
    return {
        "baseline": DummyClassifier(strategy="most_frequent"),
        "logistic_regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")),
        "random_forest": RandomForestClassifier(n_estimators=200, max_depth=8, min_samples_leaf=5, random_state=42, n_jobs=1, class_weight="balanced_subsample"),
        "xgboost": XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=42, n_jobs=1, eval_metric="logloss", scale_pos_weight=scale_pos_weight),
        "lightgbm": LGBMClassifier(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=42, n_jobs=1, verbosity=-1, class_weight="balanced"),
        "catboost": CatBoostClassifier(iterations=100, depth=4, learning_rate=0.05, random_seed=42, verbose=False, thread_count=1, auto_class_weights="Balanced"),
    }


def positive_probabilities(model, values):
    probabilities = model.predict_proba(values)
    classes = list(model.classes_)
    if 1 not in classes:
        return [0.0] * len(values)
    return probabilities[:, classes.index(1)]


def select_threshold(
    y_true,
    probabilities,
    future_returns,
    *,
    holding_period: int,
    cost_rate: float,
    min_trades: int = 5,
) -> tuple[float, dict]:
    candidates = []
    for threshold in THRESHOLD_GRID:
        predictions = [int(value >= threshold) for value in probabilities]
        metrics = evaluate_predictions(
            y_true,
            predictions,
            probabilities,
            future_returns,
            holding_period=holding_period,
            cost_rate=cost_rate,
        )
        if metrics["trade_count"] >= min_trades:
            candidates.append((metrics["strategy_return"], metrics["f1"], threshold, metrics))
    if not candidates:
        threshold = 0.5
        predictions = [int(value >= threshold) for value in probabilities]
        return threshold, evaluate_predictions(
            y_true,
            predictions,
            probabilities,
            future_returns,
            holding_period=holding_period,
            cost_rate=cost_rate,
        )
    _, _, threshold, metrics = max(
        candidates,
        key=lambda item: (item[0], item[1], item[2]),
    )
    return threshold, metrics


def train_candidates(rows: list[dict], feature_names: list[str], train_size: int, artifact_dir: str, version: str, algorithms: set[str] | None = None, *, holding_period: int = 1, cost_rate: float = 0.0015):
    x = [[row["features"][name] for name in feature_names] for row in rows]
    y = [row["label"] for row in rows]
    returns = [row["future_return"] for row in rows]
    purged_train_size = train_size - holding_period
    if purged_train_size < 50:
        raise ValueError("dataset insuficiente após purga temporal")
    x_train, x_test = x[:purged_train_size], x[train_size:]
    y_train, y_test = y[:purged_train_size], y[train_size:]
    validation_size = max(20, int(purged_train_size * 0.2))
    fit_size = purged_train_size - validation_size
    if fit_size < 30:
        raise ValueError("dataset insuficiente para treino e validação temporal")
    x_fit, x_validation = x_train[:fit_size], x_train[fit_size:]
    y_fit, y_validation = y_train[:fit_size], y_train[fit_size:]
    validation_returns = returns[fit_size:purged_train_size]
    models = build_models(y_train)
    target = Path(artifact_dir)
    target.mkdir(parents=True, exist_ok=True)
    results = []
    for name, model in models.items():
        if algorithms is not None and name not in algorithms:
            continue
        model.fit(x_fit, y_fit)
        validation_probabilities = positive_probabilities(model, x_validation)
        threshold, validation_metrics = select_threshold(
            y_validation,
            validation_probabilities,
            validation_returns,
            holding_period=holding_period,
            cost_rate=cost_rate,
        )
        model.fit(x_train, y_train)
        probabilities = positive_probabilities(model, x_test)
        predictions = [int(value >= threshold) for value in probabilities]
        metrics = evaluate_predictions(
            y_test,
            predictions,
            probabilities,
            returns[train_size:],
            holding_period=holding_period,
            cost_rate=cost_rate,
        )
        metrics.update({
            "threshold": threshold,
            "validation_strategy_return": validation_metrics["strategy_return"],
            "validation_trade_count": validation_metrics["trade_count"],
            "validation_split": "last_20_percent_of_training_window",
            "temporal_purge_rows": holding_period,
        })
        metrics.update(
            evaluate_walk_forward(
                name,
                x_train,
                y_train,
                returns[:purged_train_size],
                holding_period=holding_period,
                cost_rate=cost_rate,
            )
        )
        path = target / f"{version}-{name}.joblib"
        joblib.dump({"model": model, "threshold": threshold}, path)
        results.append((name, metrics, str(path)))
    return results


def evaluate_walk_forward(
    algorithm: str,
    x,
    y,
    future_returns,
    *,
    holding_period: int,
    cost_rate: float,
) -> dict:
    fold_metrics = []
    for fold_number, (train_end, test_end) in enumerate(
        build_walk_forward_splits(
            len(x),
            minimum_initial_train=50 + holding_period,
        ),
        start=1,
    ):
        purged_train_end = train_end - holding_period
        validation_size = max(20, int(purged_train_end * 0.2))
        fit_end = purged_train_end - validation_size
        if fit_end < 30:
            continue

        model = build_models(y[:purged_train_end])[algorithm]
        model.fit(x[:fit_end], y[:fit_end])
        validation_probabilities = positive_probabilities(
            model,
            x[fit_end:purged_train_end],
        )
        threshold, _ = select_threshold(
            y[fit_end:purged_train_end],
            validation_probabilities,
            future_returns[fit_end:purged_train_end],
            holding_period=holding_period,
            cost_rate=cost_rate,
        )
        model.fit(x[:purged_train_end], y[:purged_train_end])
        probabilities = positive_probabilities(model, x[train_end:test_end])
        predictions = [int(value >= threshold) for value in probabilities]
        metrics = evaluate_predictions(
            y[train_end:test_end],
            predictions,
            probabilities,
            future_returns[train_end:test_end],
            holding_period=holding_period,
            cost_rate=cost_rate,
        )
        fold_metrics.append({
            "fold": fold_number,
            "train_size": purged_train_end,
            "test_size": test_end - train_end,
            "purged_rows": holding_period,
            "threshold": threshold,
            "f1": metrics["f1"],
            "roc_auc": metrics["roc_auc"],
            "strategy_return": metrics["strategy_return"],
            "buy_and_hold_return": metrics["buy_and_hold_return"],
            "trade_count": metrics["trade_count"],
        })
    return aggregate_walk_forward_metrics(fold_metrics)
