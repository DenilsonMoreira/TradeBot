import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.binance.client import BinanceTestnetClient
from app.database import Base, SessionLocal, engine
from app.models import BotMode, BotStatus, Position, PositionStatus, Signal
from app.services.trading_service import (
    can_open_automatic_position,
    execute_market_buy,
    execute_market_sell,
)
from app.strategy import calculate_ema_rsi_signal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
TIMEFRAME = "15m"
# TIMEFRAME = "1m"
CANDLE_LIMIT = 100
CHECK_INTERVAL_SECONDS = 60
# CHECK_INTERVAL_SECONDS = 15

last_processed_candle: dict[str, int] = {}
last_signal_by_symbol: dict[str, str] = {}


def get_mode() -> BotMode:
    with SessionLocal() as db:
        status = db.get(BotStatus, 1)
        return status.mode if status else BotMode.OFF


def signal_already_exists(
    symbol: str,
    timeframe: str,
    signal_type: str,
    candle_time: int,
) -> bool:
    candle_marker = f"candle_open_time={candle_time}"

    with SessionLocal() as db:
        statement = (
            select(Signal.id)
            .where(
                Signal.symbol == symbol,
                Signal.timeframe == timeframe,
                Signal.signal_type == signal_type,
                Signal.details.contains(candle_marker),
            )
            .limit(1)
        )
        return db.scalar(statement) is not None


def save_signal(
    symbol: str,
    signal: dict,
    mode: BotMode,
    candle_time: int,
) -> None:
    if signal_already_exists(
        symbol=symbol,
        timeframe=TIMEFRAME,
        signal_type=signal["signal_type"],
        candle_time=candle_time,
    ):
        return

    details = (
        f"{signal['details']} "
        f"| candle_open_time={candle_time} "
        f"| bot_mode={mode.value}"
    )

    with SessionLocal() as db:
        db.add(
            Signal(
                symbol=symbol,
                timeframe=TIMEFRAME,
                signal_type=signal["signal_type"],
                price=signal["price"],
                confidence=signal["confidence"],
                strategy_name="EMA_RSI_V1",
                details=details,
            )
        )
        db.commit()

    logger.info(
        "%s | %s | preço=%s | modo=%s",
        symbol,
        signal["signal_type"],
        signal["price"],
        mode.value,
    )


async def process_symbol(
    client: BinanceTestnetClient,
    symbol: str,
    mode: BotMode,
) -> None:
    candles = await client.get_candles(
        symbol=symbol,
        interval=TIMEFRAME,
        limit=CANDLE_LIMIT,
    )

    # -2 é o último candle fechado; -1 ainda está em formação.
    closed_candle_open_time = int(candles[-2][0])

    if last_processed_candle.get(symbol) == closed_candle_open_time:
        return

    signal = calculate_ema_rsi_signal(candles)
    previous_signal = last_signal_by_symbol.get(symbol)

    # Salva BUY/SELL sempre. HOLD só é salvo quando mudou.
    should_save = (
        signal["signal_type"] in {"BUY", "SELL"}
        or previous_signal != signal["signal_type"]
    )

    if should_save:
        save_signal(
            symbol=symbol,
            signal=signal,
            mode=mode,
            candle_time=closed_candle_open_time,
        )
        if (
            mode == BotMode.TESTNET_TRADING
            and symbol == "BTCUSDT"
            and signal["signal_type"] == "BUY"
        ):
            with SessionLocal() as db:
                allowed, reason = can_open_automatic_position(
                    db=db,
                    symbol=symbol,
                )

                if allowed:
                    logger.warning(
                        "%s | BUY automático autorizado. "
                        "Enviando ordem Testnet.",
                        symbol,
                    )

                    await execute_market_buy(
                        db=db,
                        client=client,
                        symbol=symbol,
                    )
                else:
                    logger.info(
                        "%s | BUY automático bloqueado: %s",
                        symbol,
                        reason,
                    )

    last_processed_candle[symbol] = closed_candle_open_time
    last_signal_by_symbol[symbol] = signal["signal_type"]

async def manage_open_positions(
    client: BinanceTestnetClient,
    mode: BotMode,
) -> None:
    if mode != BotMode.TESTNET_TRADING:
        return

    with SessionLocal() as db:
        positions = list(
            db.scalars(
                select(Position).where(
                    Position.status == PositionStatus.OPEN
                )
            ).all()
        )

        for position in positions:
            current_price = await client.get_current_price(position.symbol)

            if (
                position.stop_loss is not None
                and current_price <= position.stop_loss
            ):
                logger.warning(
                    "%s atingiu STOP_LOSS: preço=%s, limite=%s",
                    position.symbol,
                    current_price,
                    position.stop_loss,
                )
                await execute_market_sell(
                    db=db,
                    client=client,
                    symbol=position.symbol,
                    close_reason="STOP_LOSS",
                )
                continue

            if (
                position.take_profit is not None
                and current_price >= position.take_profit
            ):
                logger.info(
                    "%s atingiu TAKE_PROFIT: preço=%s, alvo=%s",
                    position.symbol,
                    current_price,
                    position.take_profit,
                )
                await execute_market_sell(
                    db=db,
                    client=client,
                    symbol=position.symbol,
                    close_reason="TAKE_PROFIT",
                )

async def run_worker() -> None:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        status = db.get(BotStatus, 1)
        if status is None:
            db.add(BotStatus(id=1, mode=BotMode.OFF))
            db.commit()

    client = BinanceTestnetClient()

    logger.info("Worker iniciado. Símbolos: %s", ", ".join(SYMBOLS))

    while True:
        try:
            mode = get_mode()

            if mode == BotMode.OFF:
                logger.info("Bot OFF. Aguardando próxima verificação.")
            else:
                for symbol in SYMBOLS:
                    await process_symbol(client, symbol, mode)

                await manage_open_positions(client, mode)

                if mode == BotMode.TESTNET_TRADING:
                    logger.info(
                        "Modo TESTNET_TRADING ativo; posições abertas estão sendo monitoradas."
                    )

        except Exception:
            logger.exception("Erro no ciclo do worker")

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(run_worker())
