from fastapi.testclient import TestClient

from app.api.main import app
from app.database import SessionLocal
from app.models import TradingRiskSettings


def test_risk_settings_update_is_persisted() -> None:
    payload = {
        "auto_entry_enabled": False,
        "max_quote_amount_per_trade": 5.0,
        "max_daily_loss": 75.0,
        "max_open_positions": 1,
        "cooldown_minutes": 45,
    }

    with TestClient(app) as client:
        response = client.put("/trading/risk-settings", json=payload)

    assert response.status_code == 200
    assert response.json()["max_quote_amount_per_trade"] == 5.0
    assert response.json()["max_daily_loss"] == 75.0
    assert response.json()["cooldown_minutes"] == 45

    with SessionLocal() as session:
        saved = session.get(TradingRiskSettings, 1)
        assert saved is not None
        assert saved.max_quote_amount_per_trade == 5.0
        assert saved.max_daily_loss == 75.0
        assert saved.cooldown_minutes == 45
