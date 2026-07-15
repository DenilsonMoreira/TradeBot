import argparse
import asyncio
import json
import sys
from pathlib import Path

import httpx
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.binance.client import BinanceTestnetClient
from app.config import settings
from app.core.security import create_session
from app.database import SessionLocal
from app.models import Order, OrderStatus, Position, PositionStatus
from app.repositories.audit_repository import AuditRepository
from app.repositories.notification_repository import NotificationRepository
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recupera posição Testnet abaixo do mínimo nocional.",
    )
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--top-up-usdt", type=float, default=6.0)
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    if args.confirmation != "RECUPERAR POSICAO TESTNET":
        raise SystemExit("Confirmação inválida.")
    if not settings.binance_testnet:
        raise SystemExit("Recuperação permitida somente na Testnet.")

    client = BinanceTestnetClient()
    with SessionLocal() as db:
        position = db.scalar(
            select(Position).where(
                Position.symbol == "BTCUSDT",
                Position.status == PositionStatus.OPEN,
            )
        )
        if position is None:
            raise SystemExit("Nenhuma posição BTCUSDT aberta para recuperar.")

        top_up = Order(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            status=OrderStatus.PENDING,
            requested_quote_amount=args.top_up_usdt,
        )
        db.add(top_up)
        db.commit()
        db.refresh(top_up)

        try:
            response = await client.create_market_buy_order(
                "BTCUSDT",
                args.top_up_usdt,
            )
            quantity = float(response["executedQty"])
            quote = float(response["cummulativeQuoteQty"])
            if quantity <= 0 or quote <= 0:
                raise ValueError("A Binance retornou reforço inválido.")

            previous_quantity = position.quantity
            previous_invested = position.invested_quote_amount
            combined_quantity = previous_quantity + quantity
            combined_invested = previous_invested + quote
            combined_entry_price = combined_invested / combined_quantity

            top_up.status = OrderStatus.FILLED
            top_up.exchange_order_id = str(response["orderId"])
            top_up.executed_quantity = quantity
            top_up.executed_price = quote / quantity
            top_up.raw_response = json.dumps(response)
            position.quantity = combined_quantity
            position.invested_quote_amount = combined_invested
            position.entry_price = combined_entry_price
            position.stop_loss = combined_entry_price * 0.98
            position.take_profit = combined_entry_price * 1.04
            db.commit()
        except Exception as error:
            top_up.status = OrderStatus.REJECTED
            top_up.error_message = str(error)
            db.commit()
            raise

        AuditService(AuditRepository(db)).record(
            settings.auth_operator_email,
            "TESTNET_MIN_NOTIONAL_RECOVERY_TOP_UP",
            "order",
            resource_id=str(top_up.id),
            details={
                "symbol": "BTCUSDT",
                "quote_amount": args.top_up_usdt,
                "environment": "testnet",
            },
        )
        NotificationService(NotificationRepository(db)).create(
            settings.auth_operator_email,
            "WARNING",
            "TESTNET_RECOVERY",
            "Posição Testnet reforçada para saída",
            "Foi adicionado saldo simulado à posição BTC para superar o mínimo nocional.",
            resource_id=str(top_up.id),
        )
        print({
            "top_up_order_id": str(top_up.id),
            "combined_quantity": position.quantity,
            "combined_invested": position.invested_quote_amount,
        })

    token, session = create_session(
        settings.auth_operator_email,
        settings.auth_secret_key,
        10,
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-CSRF-Token": session.csrf_token,
    }
    async with httpx.AsyncClient(
        base_url="http://api:8000",
        headers=headers,
        timeout=30,
    ) as api:
        risk = (await checked(api.get("/trading/risk-settings"))).json()
        sell = (await checked(api.post(
            "/trading/manual-sell",
            json={"confirmation": "VENDER BTC TESTNET"},
        ))).json()
        await checked(api.put("/bot/status", json={"mode": "MONITOR"}))
        await checked(api.put(
            "/trading/risk-settings",
            json={
                "auto_entry_enabled": True,
                "max_quote_amount_per_trade": 6,
                "max_daily_loss": risk["max_daily_loss"],
                "max_open_positions": risk["max_open_positions"],
                "cooldown_minutes": risk["cooldown_minutes"],
                "confirmation": "ATIVAR ENTRADA AUTOMATICA",
            },
        ))
        print({
            "sell_order_id": sell["id"],
            "sell_status": sell["status"],
            "restored_mode": "MONITOR",
            "restored_auto_entry": True,
            "new_minimum_quote": 6,
        })


async def checked(request: object) -> httpx.Response:
    response = await request
    if response.is_error:
        raise RuntimeError(
            f"API {response.request.method} {response.request.url.path} "
            f"respondeu {response.status_code}: {response.text[:500]}"
        )
    return response


if __name__ == "__main__":
    asyncio.run(main())
