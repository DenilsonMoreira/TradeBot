from unittest.mock import Mock, patch

import pytest

from app.ai.registry import ModelRegistry
from app.services.prediction_service import PredictionService


def test_prediction_requires_active_model() -> None:
    repository = Mock()
    repository.get_dataset.return_value = Mock(feature_names=["return_1"])
    repository.get_active_model.return_value = None

    with pytest.raises(ValueError, match="ativo"):
        PredictionService(repository).predict(1, 10, {"return_1": 0.1})


def test_prediction_is_persisted_and_idempotent() -> None:
    repository = Mock()
    repository.session = Mock()
    repository.get_dataset.return_value = Mock(feature_names=["return_1"])
    repository.get_active_model.return_value = Mock(
        id=5,
        algorithm="logistic_regression",
        artifact_path="/tmp/model.joblib",
    )
    repository.get_prediction.side_effect = [None, Mock(id=99)]
    repository.save.side_effect = lambda item: item

    with patch(
        "app.services.prediction_service.predict_probability",
        return_value=(0.72, 0.5),
    ):
        service = PredictionService(repository)
        first = service.predict(1, 10, {"return_1": 0.1})
        second = service.predict(1, 10, {"return_1": 0.1})

    assert first.signal == "BUY"
    assert float(first.probability) == 0.72
    assert second.id == 99
    repository.session.commit.assert_called_once_with()


def test_recommendation_prefers_financial_return_then_f1() -> None:
    repository = Mock()
    lower = Mock(
        algorithm="logistic_regression",
        status="CANDIDATE",
        metrics={"strategy_return": 0.01, "f1": 0.9},
    )
    higher = Mock(
        algorithm="ensemble_soft_voting",
        status="CANDIDATE",
        metrics={"strategy_return": 0.02, "f1": 0.7},
    )
    repository.get_models_for_dataset.return_value = [lower, higher]

    assert ModelRegistry(repository).recommend(1) is higher
