from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Candle,
    Order,
    OrderStatus,
    Position,
    PositionStatus,
    Signal,
    TestnetSoakCampaign,
    TradingRiskSettings,
)


DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
DEFAULT_INTERVAL = "15m"
MONITORED_CHECKS = {
    "feeds_fresh": "Feeds de mercado atrasados",
    "no_rejected_orders": "Ordem Testnet rejeitada",
    "loss_within_limit": "Limite de perda da campanha atingido",
    "exposure_within_budget": "Exposição acima do orçamento experimental",
    "order_limits_respected": "Ordem acima do limite por operação",
    "automatic_entries_disabled": "Entrada automática reativada durante a observação",
}


class TestnetSoakService:
    def __init__(self, db: Session):
        self.db = db

    def latest(self) -> TestnetSoakCampaign | None:
        return self.db.scalar(
            select(TestnetSoakCampaign)
            .order_by(TestnetSoakCampaign.started_at.desc())
            .limit(1)
        )

    def active(self) -> TestnetSoakCampaign | None:
        return self.db.scalar(
            select(TestnetSoakCampaign)
            .where(TestnetSoakCampaign.status == "RUNNING")
            .limit(1)
        )

    def start(
        self,
        *,
        budget_brl: float = 500.0,
        reference_brl_per_usdt: float = 5.0,
        max_quote_per_trade: float = 6.0,
        max_loss_quote: float = 5.0,
        duration_hours: int = 168,
        symbols: list[str] | None = None,
    ) -> TestnetSoakCampaign:
        if self.active() is not None:
            raise ValueError("Já existe uma campanha Testnet contínua em andamento.")
        risk = self.db.get(TradingRiskSettings, 1)
        if risk is not None and risk.auto_entry_enabled:
            raise ValueError(
                "Desative a entrada automática antes de iniciar a campanha observacional."
            )
        symbols = [item.upper() for item in (symbols or DEFAULT_SYMBOLS)]
        now = datetime.now(timezone.utc)
        budget_brl_decimal = Decimal(str(budget_brl))
        reference_decimal = Decimal(str(reference_brl_per_usdt))
        quote_quantum = Decimal("0.00000001")
        baseline = {
            symbol: int(self.db.scalar(
                select(func.count(Candle.id)).where(
                    Candle.symbol == symbol,
                    Candle.interval == DEFAULT_INTERVAL,
                    Candle.is_closed.is_(True),
                )
            ) or 0)
            for symbol in symbols
        }
        campaign = TestnetSoakCampaign(
            status="RUNNING",
            budget_brl=budget_brl_decimal,
            reference_brl_per_usdt=reference_decimal,
            budget_quote=(budget_brl_decimal / reference_decimal).quantize(quote_quantum),
            max_quote_per_trade=Decimal(str(max_quote_per_trade)),
            max_loss_quote=Decimal(str(max_loss_quote)),
            duration_hours=duration_hours,
            symbols=symbols,
            baseline_candle_counts=baseline,
            result={},
            started_at=now,
            ends_at=now + timedelta(hours=duration_hours),
        )
        self.db.add(campaign)
        self.db.flush()
        return campaign

    def metrics(self, campaign: TestnetSoakCampaign) -> dict:
        now = datetime.now(timezone.utc)
        expected_per_symbol = campaign.duration_hours * 4
        candles: dict[str, dict] = {}
        for symbol in campaign.symbols:
            total = int(self.db.scalar(
                select(func.count(Candle.id)).where(
                    Candle.symbol == symbol,
                    Candle.interval == DEFAULT_INTERVAL,
                    Candle.is_closed.is_(True),
                )
            ) or 0)
            collected = max(0, total - int(campaign.baseline_candle_counts.get(symbol, 0)))
            latest_close = self.db.scalar(
                select(func.max(Candle.close_time)).where(
                    Candle.symbol == symbol,
                    Candle.interval == DEFAULT_INTERVAL,
                    Candle.is_closed.is_(True),
                )
            )
            candles[symbol] = {
                "collected": collected,
                "expected": expected_per_symbol,
                "coverage_percent": round(min(100.0, collected / max(expected_per_symbol, 1) * 100), 2),
                "latest_close_time": latest_close.isoformat() if latest_close else None,
                "fresh": bool(latest_close and (now - latest_close).total_seconds() <= 30 * 60),
            }

        order_count = int(self.db.scalar(
            select(func.count(Order.id)).where(Order.created_at >= campaign.started_at)
        ) or 0)
        rejected_orders = int(self.db.scalar(
            select(func.count(Order.id)).where(
                Order.created_at >= campaign.started_at,
                Order.status == OrderStatus.REJECTED,
            )
        ) or 0)
        max_requested = float(self.db.scalar(
            select(func.coalesce(func.max(Order.requested_quote_amount), 0.0)).where(
                Order.created_at >= campaign.started_at,
                Order.side == "BUY",
            )
        ) or 0.0)
        realized_pnl = float(self.db.scalar(
            select(func.coalesce(func.sum(Position.realized_pnl), 0.0)).where(
                Position.status == PositionStatus.CLOSED,
                Position.closed_at >= campaign.started_at,
            )
        ) or 0.0)
        open_exposure = float(self.db.scalar(
            select(func.coalesce(func.sum(Position.invested_quote_amount), 0.0)).where(
                Position.status == PositionStatus.OPEN,
            )
        ) or 0.0)
        signal_count = int(self.db.scalar(
            select(func.count(Signal.id)).where(Signal.created_at >= campaign.started_at)
        ) or 0)
        risk = self.db.get(TradingRiskSettings, 1)
        elapsed_seconds = max(0.0, (now - campaign.started_at).total_seconds())
        duration_seconds = campaign.duration_hours * 3600
        finished_time = now >= campaign.ends_at
        checks = {
            "duration_complete": finished_time,
            "candle_coverage": all(item["coverage_percent"] >= 95.0 for item in candles.values()),
            "feeds_fresh": all(item["fresh"] for item in candles.values()),
            "no_rejected_orders": rejected_orders == 0,
            "loss_within_limit": realized_pnl > -float(campaign.max_loss_quote),
            "exposure_within_budget": open_exposure <= float(campaign.budget_quote),
            "order_limits_respected": max_requested <= float(campaign.max_quote_per_trade),
            "automatic_entries_disabled": bool(risk is None or not risk.auto_entry_enabled),
        }
        return {
            "elapsed_percent": round(min(100.0, elapsed_seconds / max(duration_seconds, 1) * 100), 2),
            "remaining_hours": round(max(0.0, (campaign.ends_at - now).total_seconds() / 3600), 2),
            "candles": candles,
            "signal_count": signal_count,
            "order_count": order_count,
            "rejected_orders": rejected_orders,
            "max_requested_quote": max_requested,
            "realized_pnl_quote": round(realized_pnl, 8),
            "open_exposure_quote": round(open_exposure, 8),
            "checks": checks,
            "approved": finished_time and all(checks.values()),
        }

    def status(self) -> dict:
        campaign = self.active() or self.latest()
        if campaign is None:
            return {"campaign": None, "metrics": None}
        if campaign.status != "RUNNING" and campaign.result:
            metrics = campaign.result
        else:
            metrics = self.metrics(campaign)
            metrics["monitoring"] = campaign.result or {}
        return {"campaign": campaign, "metrics": metrics}

    def monitor_cycle(self) -> dict | None:
        campaign = self.active()
        if campaign is None:
            return None

        now = datetime.now(timezone.utc)
        metrics = self.metrics(campaign)
        previous = dict(campaign.result or {})
        previous_active = set(previous.get("active_alerts", []))
        current_active = {
            key
            for key in MONITORED_CHECKS
            if not metrics["checks"].get(key, False)
        }
        new_alerts = sorted(current_active - previous_active)
        recovered_alerts = sorted(previous_active - current_active)
        history = list(previous.get("alert_history", []))
        history.extend(
            {
                "check": key,
                "state": "ACTIVE",
                "occurred_at": now.isoformat(),
            }
            for key in new_alerts
        )
        history.extend(
            {
                "check": key,
                "state": "RECOVERED",
                "occurred_at": now.isoformat(),
            }
            for key in recovered_alerts
        )
        monitoring = {
            "active_alerts": sorted(current_active),
            "last_checked_at": now.isoformat(),
            "alert_history": history[-100:],
        }
        campaign.result = monitoring

        completed = now >= campaign.ends_at
        if completed:
            final_result = dict(metrics)
            final_result["monitoring"] = monitoring
            campaign.status = "COMPLETED" if metrics["approved"] else "FAILED"
            campaign.result = final_result
            campaign.completed_at = now

        self.db.commit()
        return {
            "campaign": campaign,
            "metrics": metrics,
            "new_alerts": new_alerts,
            "recovered_alerts": recovered_alerts,
            "completed": completed,
        }

    def complete_if_due(self) -> TestnetSoakCampaign | None:
        event = self.monitor_cycle()
        if event is None or not event["completed"]:
            return None
        return event["campaign"]


def validate_active_soak_limits(db: Session, quote_amount: float) -> tuple[bool, str]:
    service = TestnetSoakService(db)
    campaign = service.active()
    if campaign is None:
        return True, "Nenhuma campanha Testnet contínua ativa."
    metrics = service.metrics(campaign)
    max_quote_per_trade = float(campaign.max_quote_per_trade)
    budget_quote = float(campaign.budget_quote)
    max_loss_quote = float(campaign.max_loss_quote)
    if quote_amount > max_quote_per_trade:
        return False, f"A campanha limita cada compra a {campaign.max_quote_per_trade:.2f} USDT."
    if metrics["open_exposure_quote"] + quote_amount > budget_quote:
        return False, f"A compra excederia o orçamento experimental de {campaign.budget_quote:.2f} USDT."
    if metrics["realized_pnl_quote"] <= -max_loss_quote:
        return False, f"A campanha atingiu a perda máxima de {campaign.max_loss_quote:.2f} USDT."
    return True, "Limites da campanha Testnet atendidos."
