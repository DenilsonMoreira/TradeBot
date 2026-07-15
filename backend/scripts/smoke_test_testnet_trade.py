import asyncio
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.core.security import create_session


BASE_URL = "http://api:8000"


async def main() -> None:
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
        base_url=BASE_URL,
        headers=headers,
        timeout=30,
    ) as client:
        status = (await checked(client.get("/bot/status"))).json()
        risk = (await checked(client.get("/trading/risk-settings"))).json()
        positions = (await checked(client.get("/positions?limit=20"))).json()
        open_positions = [item for item in positions if item["status"] == "OPEN"]
        if open_positions:
            raise SystemExit(
                "Teste cancelado: já existe uma posição aberta no banco."
            )

        original_mode = status["mode"]
        original_auto_entry = risk["auto_entry_enabled"]
        cycle_complete = False
        print({
            "original_mode": original_mode,
            "auto_entry_was_enabled": original_auto_entry,
        })

        if original_auto_entry:
            await update_risk(client, risk, auto_entry_enabled=False)
            print({"automatic_entry": "temporarily_disabled"})

        try:
            await checked(client.put(
                "/bot/status",
                json={
                    "mode": "TESTNET_TRADING",
                    "confirmation": "ATIVAR TESTNET",
                },
            ))
            buy = (await checked(client.post(
                "/trading/manual-buy",
                json={
                    "quote_amount": 6,
                    "confirmation": "COMPRAR BTC TESTNET",
                },
            ))).json()
            print({
                "buy_order_id": buy["id"],
                "status": buy["status"],
                "quantity": buy["executed_quantity"],
                "price": buy["executed_price"],
            })

            sell = (await checked(client.post(
                "/trading/manual-sell",
                json={"confirmation": "VENDER BTC TESTNET"},
            ))).json()
            print({
                "sell_order_id": sell["id"],
                "status": sell["status"],
                "quantity": sell["executed_quantity"],
                "price": sell["executed_price"],
            })
            cycle_complete = True
        finally:
            if cycle_complete:
                await checked(client.put(
                    "/bot/status",
                    json={"mode": original_mode},
                ))
                if original_auto_entry:
                    await update_risk(
                        client,
                        risk,
                        auto_entry_enabled=True,
                    )
                print({
                    "restored_mode": original_mode,
                    "restored_auto_entry": original_auto_entry,
                })
            else:
                print({
                    "safety_state": "TESTNET_TRADING with automatic entry disabled",
                    "manual_review_required": True,
                })

        final_positions = (
            await checked(client.get("/positions?limit=20"))
        ).json()
        latest = final_positions[0]
        print({
            "position_id": latest["id"],
            "position_status": latest["status"],
            "realized_pnl": latest["realized_pnl"],
        })


async def update_risk(
    client: httpx.AsyncClient,
    risk: dict,
    *,
    auto_entry_enabled: bool,
) -> None:
    payload = {
        "auto_entry_enabled": auto_entry_enabled,
        "max_quote_amount_per_trade": risk["max_quote_amount_per_trade"],
        "max_daily_loss": risk["max_daily_loss"],
        "max_open_positions": risk["max_open_positions"],
        "cooldown_minutes": risk["cooldown_minutes"],
    }
    if auto_entry_enabled:
        payload["confirmation"] = "ATIVAR ENTRADA AUTOMATICA"
    await checked(client.put("/trading/risk-settings", json=payload))


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
