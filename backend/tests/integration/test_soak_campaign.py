from datetime import datetime, timedelta, timezone
from decimal import Decimal

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
        assert isinstance(campaign.budget_brl, Decimal)
        assert isinstance(campaign.budget_quote, Decimal)
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


def test_soak_campaign_can_be_canceled_and_restarted_with_history() -> None:
    with SessionLocal() as session:
        session.execute(delete(SoakCampaign))
        set_auto_entry(session, False)
        service = SoakService(session)
        original = service.start()
        original_id = original.id

        canceled = service.cancel_active(
            reason="Interrupção controlada de infraestrutura.",
            canceled_by="test:operator",
        )
        replacement = service.start()
        session.commit()

        assert canceled.id == original_id
        assert canceled.status == "CANCELED"
        assert canceled.completed_at is not None
        assert canceled.result["cancellation"]["canceled_by"] == "test:operator"
        assert replacement.id != original_id
        assert replacement.status == "RUNNING"
        assert service.active().id == replacement.id

        session.execute(delete(SoakCampaign))
        session.commit()


def test_soak_monitor_records_new_alert_once_and_recovery() -> None:
    with SessionLocal() as session:
        session.execute(delete(SoakCampaign))
        set_auto_entry(session, False)
        service = SoakService(session)
        service.start()
        session.commit()

        service.monitor_cycle()
        set_auto_entry(session, True)
        first_alert = service.monitor_cycle()
        repeated_alert = service.monitor_cycle()
        set_auto_entry(session, False)
        recovered = service.monitor_cycle()

        assert "automatic_entries_disabled" in first_alert["new_alerts"]
        assert "automatic_entries_disabled" not in repeated_alert["new_alerts"]
        assert "automatic_entries_disabled" in recovered["recovered_alerts"]
        assert recovered["campaign"].result["last_checked_at"]

        session.execute(delete(SoakCampaign))
        session.commit()


def test_soak_monitor_completes_due_campaign_once() -> None:
    with SessionLocal() as session:
        session.execute(delete(SoakCampaign))
        set_auto_entry(session, False)
        service = SoakService(session)
        campaign = service.start()
        campaign.ends_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        session.commit()

        completed = service.monitor_cycle()
        repeated = service.monitor_cycle()

        assert completed["completed"] is True
        assert completed["campaign"].status == "FAILED"
        assert completed["campaign"].result["monitoring"]["last_checked_at"]
        assert repeated is None

        session.execute(delete(SoakCampaign))
        session.commit()
