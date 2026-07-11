import json
from pathlib import Path

import joblib


def predict_probability(
    algorithm: str,
    artifact_path: str,
    feature_vector: list[float],
    member_paths: dict[int, str] | None = None,
) -> tuple[float, float]:
    if algorithm != "ensemble_soft_voting":
        model = joblib.load(artifact_path)
        return float(model.predict_proba([feature_vector])[0][1]), 0.5

    config = json.loads(Path(artifact_path).read_text(encoding="utf-8"))
    if member_paths is None:
        raise ValueError("artefatos dos membros são obrigatórios")
    probabilities = []
    for model_id in config["member_ids"]:
        path = member_paths.get(model_id)
        if path is None:
            raise ValueError("artefato de membro não encontrado")
        model = joblib.load(path)
        probabilities.append(float(model.predict_proba([feature_vector])[0][1]))
    probability = sum(value * weight for value, weight in zip(probabilities, config["weights"]))
    return probability, float(config["threshold"])
