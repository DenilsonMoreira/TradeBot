import asyncio
import logging

from app.binance.client import BinanceTestnetClient
from app.config import settings
from app.database import SessionLocal
from app.repositories.candle_repository import CandleRepository
from app.services.candle_service import CandleService


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def run_cycle() -> None:
    symbols = [item.strip().upper() for item in settings.candle_symbols.split(",")]
    intervals = [item.strip() for item in settings.candle_intervals.split(",")]

    with SessionLocal() as session:
        service = CandleService(
            CandleRepository(session),
            BinanceTestnetClient(),
        )
        for symbol in filter(None, symbols):
            for interval in filter(None, intervals):
                try:
                    candles = await service.sync_incremental(
                        symbol,
                        interval,
                        limit=settings.candle_sync_limit,
                    )
                    logger.info(
                        "Sincronização concluída symbol=%s interval=%s candles=%s",
                        symbol,
                        interval,
                        len(candles),
                    )
                except Exception:
                    logger.exception(
                        "Falha na sincronização symbol=%s interval=%s",
                        symbol,
                        interval,
                    )


async def run_worker() -> None:
    logger.info(
        "Candle worker iniciado symbols=%s intervals=%s",
        settings.candle_symbols,
        settings.candle_intervals,
    )
    while True:
        await run_cycle()
        await asyncio.sleep(settings.candle_sync_interval_seconds)


if __name__ == "__main__":
    asyncio.run(run_worker())
