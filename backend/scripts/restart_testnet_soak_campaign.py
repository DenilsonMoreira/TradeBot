import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.database import SessionLocal
from app.models import BotMode, BotStatus, TradingRiskSettings
from app.services.soak_service import TestnetSoakService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cancela a campanha interrompida e inicia uma nova janela Testnet.",
    )
    parser.add_argument("--duration-hours", type=int, default=168)
    parser.add_argument(
        "--reason",
        required=True,
        help="Motivo preservado no resultado da campanha cancelada.",
    )
    parser.add_argument("--actor", default="system:operator")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not settings.binance_testnet:
        raise SystemExit("Recusado: BINANCE_TESTNET precisa estar habilitado.")
    if not 1 <= args.duration_hours <= 24 * 30:
        raise SystemExit("--duration-hours deve estar entre 1 e 720.")

    with SessionLocal() as session:
        bot = session.get(BotStatus, 1)
        risk = session.get(TradingRiskSettings, 1)
        if bot is None or bot.mode != BotMode.MONITOR:
            raise SystemExit("Recusado: o bot precisa estar em MONITOR.")
        if risk is not None and risk.auto_entry_enabled:
            raise SystemExit("Recusado: entradas automáticas precisam estar desabilitadas.")
        if settings.research_promote_qualified:
            raise SystemExit("Recusado: promoção automática de modelos precisa estar desabilitada.")

        service = TestnetSoakService(session)
        previous = service.active()
        canceled = None
        if previous is not None:
            canceled = service.cancel_active(
                reason=args.reason,
                canceled_by=args.actor,
            )
        campaign = service.start(duration_hours=args.duration_hours)
        session.commit()
        session.refresh(campaign)

        print(json.dumps({
            "canceled_campaign_id": canceled.id if canceled is not None else None,
            "campaign_id": campaign.id,
            "status": campaign.status,
            "started_at": campaign.started_at.isoformat(),
            "ends_at": campaign.ends_at.isoformat(),
            "duration_hours": campaign.duration_hours,
            "symbols": campaign.symbols,
            "budget_brl": str(campaign.budget_brl),
            "budget_quote": str(campaign.budget_quote),
            "max_quote_per_trade": str(campaign.max_quote_per_trade),
            "max_loss_quote": str(campaign.max_loss_quote),
            "bot_mode": bot.mode.value,
            "auto_entry_enabled": bool(risk and risk.auto_entry_enabled),
            "automatic_model_promotion": settings.research_promote_qualified,
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
