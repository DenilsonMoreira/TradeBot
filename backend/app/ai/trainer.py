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


THRESHOLD_GRID = tuple(value / 100 for value in range(50, 91, 5))


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
    x_train, x_test = x[:train_size], x[train_size:]
    y_train, y_test = y[:train_size], y[train_size:]
    validation_size = max(20, int(train_size * 0.2))
    fit_size = train_size - validation_size
    if fit_size < 30:
        raise ValueError("dataset insuficiente para treino e validação temporal")
    x_fit, x_validation = x_train[:fit_size], x_train[fit_size:]
    y_fit, y_validation = y_train[:fit_size], y_train[fit_size:]
    validation_returns = returns[fit_size:train_size]
    positive_count = sum(y_train)
    negative_count = len(y_train) - positive_count
    scale_pos_weight = negative_count / max(positive_count, 1)
    models = {
        "baseline": DummyClassifier(strategy="most_frequent"),
        "logistic_regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")),
        "random_forest": RandomForestClassifier(n_estimators=200, max_depth=8, min_samples_leaf=5, random_state=42, n_jobs=1, class_weight="balanced_subsample"),
        "xgboost": XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=42, n_jobs=1, eval_metric="logloss", scale_pos_weight=scale_pos_weight),
        "lightgbm": LGBMClassifier(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=42, n_jobs=1, verbosity=-1, class_weight="balanced"),
        "catboost": CatBoostClassifier(iterations=100, depth=4, learning_rate=0.05, random_seed=42, verbose=False, thread_count=1, auto_class_weights="Balanced"),
    }
    target = Path(artifact_dir)
    target.mkdir(parents=True, exist_ok=True)
    results = []
    for name, model in models.items():
        if algorithms is not None and name not in algorithms:
            continue
        model.fit(x_fit, y_fit)
        validation_probabilities = model.predict_proba(x_validation)[:, 1]
        threshold, validation_metrics = select_threshold(
            y_validation,
            validation_probabilities,
            validation_returns,
            holding_period=holding_period,
            cost_rate=cost_rate,
        )
        model.fit(x_train, y_train)
        probabilities = model.predict_proba(x_test)[:, 1]
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
        })
        path = target / f"{version}-{name}.joblib"
        joblib.dump({"model": model, "threshold": threshold}, path)
        results.append((name, metrics, str(path)))
    return results
