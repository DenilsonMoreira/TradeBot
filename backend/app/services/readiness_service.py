from datetime import datetime, timezone

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    BotMode,
    BotStatus,
    Order,
    OrderStatus,
    Position,
    PositionStatus,
    TrainedModel,
    TradingRiskSettings,
)
from app.services.soak_service import TestnetSoakService


class ReadinessService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _check(
        check_id: str,
        label: str,
        status: str,
        detail: str,
        *gates: str,
    ) -> dict:
        return {
            "id": check_id,
            "label": label,
            "status": status,
            "detail": detail,
            "gates": list(gates),
        }

    def report(self) -> dict:
        bot = self.db.get(BotStatus, 1)
        risk = self.db.get(TradingRiskSettings, 1)
        soak = TestnetSoakService(self.db).status()
        campaign = soak["campaign"]
        soak_metrics = soak["metrics"] or {}
        active_alerts = soak_metrics.get("monitoring", {}).get("active_alerts", [])

        current_revision = self.db.scalar(text("SELECT version_num FROM alembic_version"))
        expected_revision = ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
        open_positions = int(self.db.scalar(
            select(func.count(Position.id)).where(Position.status == PositionStatus.OPEN)
        ) or 0)
        active_models = int(self.db.scalar(
            select(func.count(TrainedModel.id)).where(TrainedModel.status == "ACTIVE")
        ) or 0)

        filled_buys = filled_sells = closed_positions = 0
        if campaign is not None:
            filled_buys = int(self.db.scalar(
                select(func.count(Order.id)).where(
                    Order.created_at >= campaign.started_at,
                    Order.side == "BUY",
                    Order.status == OrderStatus.FILLED,
                )
            ) or 0)
            filled_sells = int(self.db.scalar(
                select(func.count(Order.id)).where(
                    Order.created_at >= campaign.started_at,
                    Order.side == "SELL",
                    Order.status == OrderStatus.FILLED,
                )
            ) or 0)
            closed_positions = int(self.db.scalar(
                select(func.count(Position.id)).where(
                    Position.closed_at >= campaign.started_at,
                    Position.status == PositionStatus.CLOSED,
                )
            ) or 0)

        auth_configured = all((
            settings.auth_secret_key,
            settings.auth_operator_email,
            settings.auth_password_hash,
            settings.auth_totp_secret,
        )) and len(settings.auth_secret_key) >= 32
        feeds_fresh = bool(soak_metrics.get("checks", {}).get("feeds_fresh"))
        round_trip_ok = filled_buys > 0 and filled_sells > 0 and closed_positions > 0
        campaign_complete = campaign is not None and campaign.status != "RUNNING"
        campaign_approved = bool(soak_metrics.get("approved")) and campaign is not None and campaign.status == "COMPLETED"

        checks = [
            self._check("testnet_only", "Ambiente exclusivamente Testnet", "PASS" if settings.binance_testnet else "FAIL", "Binance Spot Testnet ativa." if settings.binance_testnet else "Ambiente real não autorizado.", "LOCAL", "SERVER", "AUTO"),
            self._check("authentication", "Autenticação e 2FA configurados", "PASS" if auth_configured else "FAIL", "Credenciais do operador e segredo de sessão configurados." if auth_configured else "Configuração de autenticação incompleta ou segredo curto.", "LOCAL", "SERVER", "AUTO"),
            self._check("database_revision", "Banco na migration atual", "PASS" if current_revision == expected_revision else "FAIL", f"Banco: {current_revision}; código: {expected_revision}.", "LOCAL", "SERVER", "AUTO"),
            self._check("safe_bot_mode", "Modo operacional seguro", "PASS" if bot and bot.mode in {BotMode.OFF, BotMode.MONITOR} else "FAIL", f"Modo atual: {bot.mode.value if bot else 'AUSENTE'}.", "LOCAL", "SERVER"),
            self._check("automatic_entries", "Entrada automática desativada", "PASS" if risk and not risk.auto_entry_enabled else "FAIL", "Nenhuma entrada automática pode ser enviada durante a validação.", "LOCAL", "SERVER"),
            self._check("open_positions", "Nenhuma posição pendente", "PASS" if open_positions == 0 else "FAIL", f"Posições abertas: {open_positions}.", "LOCAL", "SERVER"),
            self._check("market_feeds", "Feeds de mercado atuais", "PASS" if feeds_fresh else "FAIL", "BTC, ETH e BNB dentro do limite de atualização." if feeds_fresh else "Um ou mais feeds estão atrasados.", "LOCAL", "SERVER", "AUTO"),
            self._check("soak_alerts", "Campanha sem alertas ativos", "PASS" if not active_alerts else "FAIL", "Nenhum alerta ativo." if not active_alerts else f"Alertas: {', '.join(active_alerts)}.", "LOCAL", "SERVER", "AUTO"),
            self._check("execution_round_trip", "Compra e venda controladas", "PASS" if round_trip_ok else "PENDING", f"Compras: {filled_buys}; vendas: {filled_sells}; posições fechadas: {closed_positions}.", "LOCAL", "SERVER"),
            self._check("campaign_complete", "Campanha de sete dias concluída", "PASS" if campaign_complete else "PENDING", f"Status: {campaign.status if campaign else 'NÃO INICIADA'}.", "SERVER", "AUTO"),
            self._check("campaign_approved", "Campanha quantitativamente aprovada", "PASS" if campaign_approved else ("FAIL" if campaign_complete else "PENDING"), "Todos os critérios foram atendidos." if campaign_approved else "Aguardando resultado final da campanha.", "SERVER", "AUTO"),
            self._check("active_model", "Modelo aprovado e ativo", "PASS" if active_models > 0 else "PENDING", f"Modelos ativos: {active_models}.", "AUTO"),
            self._check("manual_model_promotion", "Promoção automática bloqueada", "PASS" if not settings.research_promote_qualified else "FAIL", "A promoção de modelos exige revisão explícita.", "LOCAL", "SERVER", "AUTO"),
        ]

        def gate_ready(gate: str) -> bool:
            gated = [item for item in checks if gate in item["gates"]]
            return bool(gated) and all(item["status"] == "PASS" for item in gated)

        return {
            "generated_at": datetime.now(timezone.utc),
            "environment": "TESTNET" if settings.binance_testnet else "LIVE",
            "local_stack_ready": gate_ready("LOCAL"),
            "server_release_ready": gate_ready("SERVER"),
            "automatic_trading_ready": gate_ready("AUTO"),
            "summary": {
                "passed": sum(item["status"] == "PASS" for item in checks),
                "pending": sum(item["status"] == "PENDING" for item in checks),
                "failed": sum(item["status"] == "FAIL" for item in checks),
                "total": len(checks),
            },
            "checks": checks,
        }

