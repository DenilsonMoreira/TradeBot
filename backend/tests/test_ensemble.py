from pathlib import Path

import joblib
import numpy as np
import pytest

from app.ai.ensemble import evaluate_soft_voting


class ProbabilityModel:
    def __init__(self, probabilities):
        self.probabilities = probabilities

    def predict_proba(self, values):
        return np.array(
            [[1 - probability, probability] for probability in self.probabilities]
        )


def test_soft_voting_uses_uniform_probabilities_and_oos_metrics(tmp_path: Path):
    paths = []
    for index, probabilities in enumerate(([0.8, 0.2], [0.6, 0.4])):
        path = tmp_path / f"model-{index}.joblib"
        joblib.dump(ProbabilityModel(probabilities), path)
        paths.append(str(path))

    metrics, probabilities, weights = evaluate_soft_voting(
        paths,
        [[1.0], [2.0]],
        [1, 0],
        [0.02, -0.01],
    )

    assert probabilities == [0.7, 0.30000000000000004]
    assert weights == [0.5, 0.5]
    assert metrics["accuracy"] == 1.0
    assert metrics["strategy_return"] == pytest.approx(
        (1 - 0.0015) ** 2 * 1.02 - 1
    )
