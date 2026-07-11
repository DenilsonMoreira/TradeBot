import asyncio
import logging

from app.config import settings
from app.database import SessionLocal
from app.repositories.candle_repository import CandleRepository
from app.repositories.indicator_repository import IndicatorRepository
from app.services.indicator_service import IndicatorService


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def run_cycle() -> None:
    symbols = [item.strip().upper() for item in settings.candle_symbols.split(",")]
    intervals = [item.strip() for item in settings.candle_intervals.split(",")]
    with SessionLocal() as session:
        service = IndicatorService(
            CandleRepository(session),
            IndicatorRepository(session),
            history_limit=settings.indicator_history_limit,
        )
        for symbol in filter(None, symbols):
            for interval in filter(None, intervals):
                try:
                    indicators = service.calculate_and_persist(symbol, interval)
                    logger.info(
                        "Cálculo concluído symbol=%s interval=%s indicators=%s",
                        symbol,
                        interval,
                        len(indicators),
                    )
                except Exception:
                    logger.exception(
                        "Falha no cálculo symbol=%s interval=%s",
                        symbol,
                        interval,
                    )


async def run_worker() -> None:
    logger.info("Indicator worker iniciado")
    while True:
        run_cycle()
        await asyncio.sleep(settings.indicator_calculation_interval_seconds)


if __name__ == "__main__":
    asyncio.run(run_worker())
