import hashlib
import hmac
import time
from urllib.parse import urlencode

import httpx

from app.config import settings


class BinanceTestnetClient:
    def __init__(self) -> None:
        self.base_url = (
            "https://testnet.binance.vision"
            if settings.binance_testnet
            else "https://api.binance.com"
        )

    async def get_candles(
        self,
        symbol: str,
        interval: str = "15m",
        limit: int = 100,
    ) -> list:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{self.base_url}/api/v3/klines",
                params={
                    "symbol": symbol.upper(),
                    "interval": interval,
                    "limit": limit,
                },
            )
            response.raise_for_status()
            return response.json()

    async def get_account(self) -> dict:
        timestamp = int(time.time() * 1000)
        query = urlencode({"timestamp": timestamp})
        signature = hmac.new(
            settings.binance_api_secret.encode(),
            query.encode(),
            hashlib.sha256,
        ).hexdigest()

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{self.base_url}/api/v3/account",
                params={
                    "timestamp": timestamp,
                    "signature": signature,
                },
                headers={
                    "X-MBX-APIKEY": settings.binance_api_key,
                },
            )
            response.raise_for_status()
            return response.json()