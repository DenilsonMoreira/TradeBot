from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_research_automation_service,
    get_research_repository,
)
from app.api.main import app
from app.services.research_automation_service import ResearchAutomationService


def build_service():
    candles = Mock()
    research = Mock()
    datasets = Mock()
    training = Mock()
    registry = Mock()
    service = ResearchAutomationService(
        candles,
        research,
        datasets,
        training,
        registry,
    )
    return service, candles, research, datasets, training, registry


def latest_dataset(dataset_id=10):
    return Mock(
        id=dataset_id,
        test_size=774,
        rows=[{"open_time": "2026-07-15T00:00:00+00:00"}],
    )


def test_automation_waits_for_a_completely_new_test_window():
    service, candles, research, datasets, training, registry = build_service()
    research.get_latest_dataset.return_value = latest_dataset()
    candles.count_after.return_value = 777

    result = service.evaluate_market(
        "BTCUSDT",
        "15m",
        limit=3900,
        horizon=4,
        train_ratio=0.8,
    )

    assert result["due"] is False
    assert result["required_new_candles"] == 778
    assert result["missing_candles"] == 1
    assert result["estimated_ready_at"] is not None
    datasets.build.assert_not_called()
    training.train.assert_not_called()
    registry.promote.assert_not_called()


def test_automation_trains_but_does_not_promote_by_default():
    service, candles, research, datasets, training, registry = build_service()
    service.notifications = Mock()
    service.audit = Mock()
    service.recipient = "operator@example.com"
    current = latest_dataset()
    new_dataset = latest_dataset(dataset_id=11)
    research.get_latest_dataset.return_value = current
    candles.count_after.return_value = 778
    datasets.build.return_value = new_dataset
    training.train.return_value = [
        Mock(
            algorithm=f"model_{index}",
            metrics={
                "strategy_return": -0.01,
                "walk_forward_return": -0.02,
                "walk_forward_profitable_folds": 0,
                "walk_forward_folds": 3,
                "trade_count": 10,
            },
        )
        for index in range(6)
    ]
    registry.recommend.return_value = Mock(algorithm="xgboost", id=20)

    result = service.evaluate_market(
        "BTCUSDT",
        "15m",
        limit=3900,
        horizon=4,
        train_ratio=0.8,
    )

    assert result["due"] is True
    assert result["dataset_id"] == 11
    assert result["trained_models"] == 6
    assert result["recommended"] == "xgboost"
    assert result["activated"] is None
    registry.promote.assert_not_called()
    service.notifications.create.assert_called_once()
    assert service.notifications.create.call_args.args[1:4] == (
        "info",
        "research",
        "Novo candidato para BTCUSDT",
    )
    service.audit.record.assert_called_once()


def test_automation_requires_full_history_for_first_dataset():
    service, candles, research, datasets, training, registry = build_service()
    research.get_latest_dataset.return_value = None
    candles.count.return_value = 3899

    result = service.evaluate_market(
        "ETHUSDT",
        "15m",
        limit=3900,
        horizon=4,
        train_ratio=0.8,
    )

    assert result["due"] is False
    assert result["required_new_candles"] == 3900
    datasets.build.assert_not_called()


def test_automation_status_endpoint_exposes_market_progress():
    service = Mock()
    service.get_market_status.side_effect = lambda symbol, interval, **_: {
        "symbol": symbol,
        "interval": interval,
        "due": False,
        "available_new_candles": 5,
        "required_new_candles": 778,
        "missing_candles": 773,
        "progress_percent": 5 / 778 * 100,
        "last_evaluated_at": "2026-07-15T03:45:00+00:00",
        "estimated_ready_at": "2026-07-23T05:00:00+00:00",
        "dataset_id": 27,
    }
    app.dependency_overrides[get_research_automation_service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.get("/research/automation/status")
    finally:
        app.dependency_overrides.pop(get_research_automation_service, None)

    assert response.status_code == 200
    body = response.json()
    assert len(body["markets"]) == 3
    assert body["markets"][0]["required_new_candles"] == 778
    assert body["markets"][0]["missing_candles"] == 773


def test_failed_evaluation_is_persisted_and_notified():
    candles = Mock()
    research = Mock()
    datasets = Mock()
    training = Mock()
    registry = Mock()
    notifications = Mock()
    audit = Mock()
    service = ResearchAutomationService(
        candles,
        research,
        datasets,
        training,
        registry,
        notifications,
        audit,
        "operator@example.com",
    )
    research.get_latest_dataset.return_value = latest_dataset()
    candles.count_after.return_value = 778
    datasets.build.side_effect = ValueError("série inválida")

    with pytest.raises(ValueError, match="série inválida"):
        service.evaluate_market(
            "BTCUSDT",
            "15m",
            limit=3900,
            horizon=4,
            train_ratio=0.8,
        )

    run = research.save.call_args.args[0]
    assert run.status == "FAILED"
    assert run.error_message == "série inválida"
    notifications.create.assert_called_once()
    assert notifications.create.call_args.args[1:4] == (
        "critical",
        "research",
        "Falha na avaliação de BTCUSDT",
    )
    audit.record.assert_called_once()


def test_evaluation_history_endpoint_returns_persisted_runs():
    repository = Mock()
    repository.list_evaluation_runs.return_value = [
        SimpleNamespace(
            id=1,
            symbol="BTCUSDT",
            interval="15m",
            dataset_id=27,
            status="COMPLETED",
            new_candles=778,
            required_candles=778,
            models_trained=6,
            recommended_algorithm=None,
            activated_algorithm=None,
            metrics_summary={},
            error_message=None,
            started_at=datetime(2026, 7, 15, tzinfo=UTC),
            completed_at=datetime(2026, 7, 15, 0, 2, tzinfo=UTC),
        )
    ]
    app.dependency_overrides[get_research_repository] = lambda: repository
    try:
        with TestClient(app) as client:
            response = client.get("/research/evaluations?limit=10")
    finally:
        app.dependency_overrides.pop(get_research_repository, None)

    assert response.status_code == 200
    assert response.json()[0]["status"] == "COMPLETED"
    repository.list_evaluation_runs.assert_called_once_with(10)
