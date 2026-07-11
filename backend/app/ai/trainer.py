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


def train_candidates(rows: list[dict], feature_names: list[str], train_size: int, artifact_dir: str, version: str, algorithms: set[str] | None = None):
    x = [[row["features"][name] for name in feature_names] for row in rows]
    y = [row["label"] for row in rows]
    returns = [row["future_return"] for row in rows]
    x_train, x_test = x[:train_size], x[train_size:]
    y_train, y_test = y[:train_size], y[train_size:]
    models = {
        "baseline": DummyClassifier(strategy="most_frequent"),
        "logistic_regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=42)),
        "random_forest": RandomForestClassifier(n_estimators=200, max_depth=8, min_samples_leaf=5, random_state=42, n_jobs=1),
        "xgboost": XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=42, n_jobs=1, eval_metric="logloss"),
        "lightgbm": LGBMClassifier(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=42, n_jobs=1, verbosity=-1),
        "catboost": CatBoostClassifier(iterations=100, depth=4, learning_rate=0.05, random_seed=42, verbose=False, thread_count=1),
    }
    target = Path(artifact_dir)
    target.mkdir(parents=True, exist_ok=True)
    results = []
    for name, model in models.items():
        if algorithms is not None and name not in algorithms:
            continue
        model.fit(x_train, y_train)
        predictions = model.predict(x_test)
        probabilities = model.predict_proba(x_test)[:, 1] if hasattr(model, "predict_proba") else predictions
        metrics = evaluate_predictions(y_test, predictions, probabilities, returns[train_size:])
        path = target / f"{version}-{name}.joblib"
        joblib.dump(model, path)
        results.append((name, metrics, str(path)))
    return results
