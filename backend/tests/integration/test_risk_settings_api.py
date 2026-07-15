from fastapi.testclient import TestClient

from app.api.main import app
from app.database import SessionLocal
from sqlalchemy import delete

from app.models import TestnetSoakCampaign as SoakCampaign
from app.models import TradingRiskSettings
from app.services.soak_service import TestnetSoakService as SoakService


def test_risk_settings_update_is_persisted() -> None:
    payload = {
        "auto_entry_enabled": False,
        "max_quote_amount_per_trade": 6.0,
        "max_daily_loss": 75.0,
        "max_open_positions": 1,
        "cooldown_minutes": 45,
    }

    with TestClient(app) as client:
        response = client.put("/trading/risk-settings", json=payload)

    assert response.status_code == 200
    assert response.json()["max_quote_amount_per_trade"] == 6.0
    assert response.json()["max_daily_loss"] == 75.0
    assert response.json()["cooldown_minutes"] == 45

    with SessionLocal() as session:
        saved = session.get(TradingRiskSettings, 1)
        assert saved is not None
        assert saved.max_quote_amount_per_trade == 6.0
        assert saved.max_daily_loss == 75.0
        assert saved.cooldown_minutes == 45


def test_risk_settings_cannot_enable_auto_entry_during_soak() -> None:
    with SessionLocal() as session:
        session.execute(delete(SoakCampaign))
        risk = session.get(TradingRiskSettings, 1)
        assert risk is not None
        risk.auto_entry_enabled = False
        SoakService(session).start()
        session.commit()

    payload = {
        "auto_entry_enabled": True,
        "max_quote_amount_per_trade": 6.0,
        "max_daily_loss": 75.0,
        "max_open_positions": 1,
        "cooldown_minutes": 45,
        "confirmation": "ATIVAR ENTRADA AUTOMATICA",
    }
    with TestClient(app) as client:
        response = client.put("/trading/risk-settings", json=payload)

    assert response.status_code == 400
    assert "campanha Testnet observacional" in response.json()["detail"]

    with SessionLocal() as session:
        session.execute(delete(SoakCampaign))
        session.commit()
