import pytest
from sqlalchemy import delete

from app.database import SessionLocal
from app.models import TradingRiskSettings
from app.models import TestnetSoakCampaign as SoakCampaign
from app.services.soak_service import TestnetSoakService as SoakService, validate_active_soak_limits


def set_auto_entry(session, enabled: bool) -> TradingRiskSettings:
    risk = session.get(TradingRiskSettings, 1)
    if risk is None:
        risk = TradingRiskSettings(id=1)
        session.add(risk)
    risk.auto_entry_enabled = enabled
    session.commit()
    return risk


def test_soak_campaign_persists_safe_reference_budget() -> None:
    with SessionLocal() as session:
        session.execute(delete(SoakCampaign))
        set_auto_entry(session, False)

        service = SoakService(session)
        campaign = service.start()
        session.commit()
        session.refresh(campaign)

        status = service.status()
        assert campaign.status == "RUNNING"
        assert campaign.budget_brl == 500.0
        assert campaign.budget_quote == 100.0
        assert campaign.max_quote_per_trade == 6.0
        assert campaign.max_loss_quote == 5.0
        assert campaign.duration_hours == 168
        assert status["metrics"]["checks"]["automatic_entries_disabled"] is True
        assert status["metrics"]["order_count"] == 0

        session.execute(delete(SoakCampaign))
        session.commit()


def test_active_soak_campaign_rejects_purchase_above_trade_cap() -> None:
    with SessionLocal() as session:
        session.execute(delete(SoakCampaign))
        set_auto_entry(session, False)
        SoakService(session).start()
        session.commit()

        allowed, _ = validate_active_soak_limits(session, 6.0)
        oversized, reason = validate_active_soak_limits(session, 6.01)

        assert allowed is True
        assert oversized is False
        assert "6.00 USDT" in reason

        session.execute(delete(SoakCampaign))
        session.commit()


def test_soak_campaign_requires_automatic_entries_disabled() -> None:
    with SessionLocal() as session:
        session.execute(delete(SoakCampaign))
        set_auto_entry(session, True)

        with pytest.raises(ValueError, match="Desative a entrada automática"):
            SoakService(session).start()

        set_auto_entry(session, False)
