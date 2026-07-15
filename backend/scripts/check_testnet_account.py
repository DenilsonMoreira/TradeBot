import asyncio
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.binance.client import BinanceTestnetClient
from app.config import settings


async def main() -> None:
    print({
        "testnet": settings.binance_testnet,
        "api_key_configured": bool(
            settings.binance_api_key
            and settings.binance_api_key != "change-me"
        ),
        "secret_configured": bool(
            settings.binance_api_secret
            and settings.binance_api_secret != "change-me"
        ),
    })
    try:
        account = await BinanceTestnetClient().get_account()
    except httpx.HTTPStatusError as error:
        print({
            "account_access": False,
            "status": error.response.status_code,
            "detail": error.response.text[:300],
        })
        raise SystemExit(1) from error

    configured_assets = {
        "USDT",
        *(
            symbol.strip().upper().removesuffix("USDT")
            for symbol in settings.candle_symbols.split(",")
            if symbol.strip().upper().endswith("USDT")
        ),
    }
    balances = [
        {
            "asset": balance["asset"],
            "free": balance["free"],
            "locked": balance["locked"],
        }
        for balance in account.get("balances", [])
        if balance["asset"] in configured_assets
        and (float(balance["free"]) or float(balance["locked"]))
    ]
    print({
        "account_access": True,
        "can_trade": account.get("canTrade"),
        "nonzero_balances": balances,
    })


if __name__ == "__main__":
    asyncio.run(main())
