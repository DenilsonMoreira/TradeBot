import hashlib
import hmac
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

    async def get_server_time(self) -> int:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(f"{self.base_url}/api/v3/time")
            response.raise_for_status()
            return response.json()["serverTime"]

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
        timestamp = await self.get_server_time()

        params = {
            "timestamp": timestamp,
            "recvWindow": 10_000,
        }

        query = urlencode(params)
        signature = hmac.new(
            settings.binance_api_secret.encode(),
            query.encode(),
            hashlib.sha256,
        ).hexdigest()

        params["signature"] = signature

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{self.base_url}/api/v3/account",
                params=params,
                headers={"X-MBX-APIKEY": settings.binance_api_key},
            )
            response.raise_for_status()
            return response.json()

    async def create_market_buy_order(
        self,
        symbol: str,
        quote_order_qty: float,
    ) -> dict:
        timestamp = await self.get_server_time()

        params = {
            "symbol": symbol.upper(),
            "side": "BUY",
            "type": "MARKET",
            "quoteOrderQty": f"{quote_order_qty:.2f}",
            "newOrderRespType": "FULL",
            "recvWindow": 10_000,
            "timestamp": timestamp,
        }

        query = urlencode(params)
        signature = hmac.new(
            settings.binance_api_secret.encode(),
            query.encode(),
            hashlib.sha256,
        ).hexdigest()

        params["signature"] = signature

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{self.base_url}/api/v3/order",
                params=params,
                headers={"X-MBX-APIKEY": settings.binance_api_key},
            )
            response.raise_for_status()
            return response.json()
    
    async def create_market_sell_order(
        self,
        symbol: str,
        quantity: float,
    ) -> dict:
        timestamp = await self.get_server_time()

        params = {
            "symbol": symbol.upper(),
            "side": "SELL",
            "type": "MARKET",
            "quantity": f"{quantity:.8f}",
            "newOrderRespType": "FULL",
            "recvWindow": 10_000,
            "timestamp": timestamp,
        }

        query = urlencode(params)
        signature = hmac.new(
            settings.binance_api_secret.encode(),
            query.encode(),
            hashlib.sha256,
        ).hexdigest()

        params["signature"] = signature

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{self.base_url}/api/v3/order",
                params=params,
                headers={"X-MBX-APIKEY": settings.binance_api_key},
            )
            response.raise_for_status()
            return response.json()

    async def get_current_price(self, symbol: str) -> float:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{self.base_url}/api/v3/ticker/price",
                params={"symbol": symbol.upper()},
            )
            response.raise_for_status()
            return float(response.json()["price"])