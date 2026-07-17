from pathlib import Path

import joblib


def validate_model_artifact(path: str, feature_vector: list[float] | None = None) -> tuple[bool, str | None]:
    target = Path(path)
    if not target.is_file() or target.stat().st_size == 0:
        return False, "arquivo ausente ou vazio"
    try:
        artifact = joblib.load(target)
        model = artifact.get("model") if isinstance(artifact, dict) else artifact
        threshold = artifact.get("threshold", 0.5) if isinstance(artifact, dict) else 0.5
        if model is None or not hasattr(model, "predict_proba"):
            return False, "modelo sem predict_proba"
        if not 0 <= float(threshold) <= 1:
            return False, "threshold fora do intervalo"
        if feature_vector is not None:
            probabilities = model.predict_proba([feature_vector])
            if len(probabilities) != 1:
                return False, "saída de probabilidade inválida"
        return True, None
    except Exception as error:
        return False, str(error)
