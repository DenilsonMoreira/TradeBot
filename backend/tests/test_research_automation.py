from unittest.mock import Mock

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
    datasets.build.assert_not_called()
    training.train.assert_not_called()
    registry.promote.assert_not_called()


def test_automation_trains_but_does_not_promote_by_default():
    service, candles, research, datasets, training, registry = build_service()
    current = latest_dataset()
    new_dataset = latest_dataset(dataset_id=11)
    research.get_latest_dataset.return_value = current
    candles.count_after.return_value = 778
    datasets.build.return_value = new_dataset
    training.train.return_value = [Mock() for _ in range(6)]
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
