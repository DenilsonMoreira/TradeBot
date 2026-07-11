from collections.abc import Sequence

import joblib

from app.ai.evaluator import evaluate_predictions


def evaluate_soft_voting(
    artifact_paths: Sequence[str],
    x_test: list[list[float]],
    y_test: list[int],
    future_returns: list[float],
    *,
    threshold: float = 0.5,
) -> tuple[dict, list[float], list[float]]:
    if len(artifact_paths) < 2:
        raise ValueError("ensemble requer ao menos dois modelos")
    if not 0 < threshold < 1:
        raise ValueError("threshold deve estar entre 0 e 1")

    probabilities_by_model = []
    for path in artifact_paths:
        model = joblib.load(path)
        if not hasattr(model, "predict_proba"):
            raise ValueError("todos os modelos devem fornecer probabilidades")
        probabilities_by_model.append(model.predict_proba(x_test)[:, 1])

    weight = 1.0 / len(probabilities_by_model)
    weights = [weight] * len(probabilities_by_model)
    probabilities = [
        sum(model_values[index] * model_weight for model_values, model_weight in zip(probabilities_by_model, weights))
        for index in range(len(x_test))
    ]
    predictions = [int(value >= threshold) for value in probabilities]
    metrics = evaluate_predictions(
        y_test,
        predictions,
        probabilities,
        future_returns,
    )
    return metrics, probabilities, weights
