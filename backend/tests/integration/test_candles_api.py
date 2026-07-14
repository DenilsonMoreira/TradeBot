from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.api.dependencies import get_candle_service
from app.api.main import app
from app.database import SessionLocal
from app.models.candle import Candle


def make_candle(open_time: datetime, *, is_closed: bool = True) -> Candle:
    return Candle(
        symbol="BTCUSDT",
        interval="1m",
        open_time=open_time,
        close_time=open_time + timedelta(seconds=59),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("105"),
        volume=Decimal("12.5"),
        quote_volume=Decimal("1300"),
        trades=42,
        taker_buy_volume=Decimal("7"),
        taker_buy_quote=Decimal("730"),
        is_closed=is_closed,
    )


def test_candle_read_endpoints() -> None:
    open_time = datetime(2026, 7, 10, tzinfo=UTC)
    with SessionLocal() as session:
        session.execute(delete(Candle))
        session.add(make_candle(open_time))
        session.commit()

    with TestClient(app) as client:
        history = client.get(
            "/candles",
            params={"symbol": "BTCUSDT", "interval": "1m"},
        )
        latest = client.get(
            "/candles/latest",
            params={"symbol": "BTCUSDT", "interval": "1m"},
        )

    assert history.status_code == 200
    assert len(history.json()) == 1
    assert latest.status_code == 200
    assert latest.json()["symbol"] == "BTCUSDT"


def test_market_config_exposes_configured_symbols() -> None:
    with TestClient(app) as client:
        response = client.get("/candles/config")

    assert response.status_code == 200
    assert "BTCUSDT" in response.json()["symbols"]
    assert response.json()["dashboard_refresh_seconds"] == 15


def test_sync_endpoint_uses_service() -> None:
    service = AsyncMock()
    service.sync_incremental.return_value = []
    app.dependency_overrides[get_candle_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.post(
                "/candles/sync",
                json={"symbol": "btcusdt", "interval": "1m", "limit": 10},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["synchronized"] == 0
    service.sync_incremental.assert_awaited_once_with(
        "BTCUSDT", "1m", limit=10
    )


def test_latest_returns_404_when_empty() -> None:
    with SessionLocal() as session:
        session.execute(delete(Candle))
        session.commit()

    with TestClient(app) as client:
        response = client.get(
            "/candles/latest",
            params={"symbol": "BTCUSDT", "interval": "1m"},
        )

    assert response.status_code == 404
