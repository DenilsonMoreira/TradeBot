import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.models import BotMode
from app.workers import trader_worker


def test_automatic_buy_uses_configured_risk_amount() -> None:
    client = MagicMock()
    client.get_candles = AsyncMock(return_value=[[1], [2], [3]])
    db = MagicMock()
    db.get.return_value = SimpleNamespace(max_quote_amount_per_trade=5.0)
    session_context = MagicMock()
    session_context.__enter__.return_value = db
    execute_buy = AsyncMock()

    trader_worker.last_processed_candle.clear()
    trader_worker.last_signal_by_symbol.clear()
    with (
        patch.object(trader_worker, "SessionLocal", return_value=session_context),
        patch.object(trader_worker, "calculate_ema_rsi_signal", return_value={
            "signal_type": "BUY",
            "price": 100.0,
            "confidence": 80.0,
            "details": "teste",
        }),
        patch.object(trader_worker, "save_signal"),
        patch.object(trader_worker, "can_open_automatic_position", return_value=(True, "permitida")),
        patch.object(trader_worker, "execute_market_buy", execute_buy),
    ):
        asyncio.run(trader_worker.process_symbol(client, "BTCUSDT", BotMode.TESTNET_TRADING))

    execute_buy.assert_awaited_once_with(
        db=db,
        client=client,
        symbol="BTCUSDT",
        quote_amount=5.0,
    )
