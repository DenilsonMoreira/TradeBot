from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.api.dependencies import get_indicator_service
from app.api.main import app


def test_calculate_indicators_endpoint_uses_service() -> None:
    service = Mock()
    service.config_version = "technical-v1-h1000"
    service.calculate_and_persist.return_value = []
    app.dependency_overrides[get_indicator_service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.post(
                "/indicators/calculate",
                json={"symbol": "btcusdt", "interval": "15m"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "symbol": "BTCUSDT",
        "interval": "15m",
        "config_version": "technical-v1-h1000",
        "persisted": 0,
    }
    service.calculate_and_persist.assert_called_once_with("BTCUSDT", "15m")


def test_indicator_query_endpoint_passes_filters() -> None:
    service = Mock()
    service.get_history.return_value = []
    app.dependency_overrides[get_indicator_service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.get(
                "/indicators",
                params={
                    "symbol": "BTCUSDT",
                    "interval": "15m",
                    "name": "RSI_14",
                    "limit": 20,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    service.get_history.assert_called_once_with(
        "BTCUSDT",
        "15m",
        name="RSI_14",
        config_version=None,
        limit=20,
        offset=0,
    )
