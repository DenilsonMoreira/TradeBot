import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.binance.client import BinanceTestnetClient
from app.config import settings
from app.database import SessionLocal
from app.repositories.candle_repository import CandleRepository
from app.services.candle_service import CandleService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preenche candles anteriores sem duplicar os já persistidos.",
    )
    parser.add_argument("--symbols", nargs="+", help="Ex.: BTCUSDT ETHUSDT")
    parser.add_argument("--interval", default="15m")
    parser.add_argument("--target-per-market", type=int, default=3000)
    parser.add_argument("--batch-size", type=int, default=1000)
    return parser.parse_args()


async def backfill_market(
    symbol: str,
    interval: str,
    target: int,
    batch_size: int,
) -> tuple[int, int]:
    with SessionLocal() as session:
        repository = CandleRepository(session)
        service = CandleService(repository, BinanceTestnetClient())
        initial = repository.count(symbol, interval)
        current = initial

        while current < target:
            limit = min(batch_size, target - current)
            candles = await service.sync_historical_before(
                symbol,
                interval,
                limit=limit,
            )
            next_count = repository.count(symbol, interval)
            if not candles or next_count <= current:
                break
            current = next_count
            print(f"{symbol} {interval}: {current}/{target} candles")

        return initial, current


async def main() -> None:
    args = parse_args()
    if not 1 <= args.batch_size <= 1000:
        raise SystemExit("--batch-size deve estar entre 1 e 1000")
    if args.target_per_market < 1:
        raise SystemExit("--target-per-market deve ser maior que zero")

    configured = [
        item.strip().upper()
        for item in settings.candle_symbols.split(",")
        if item.strip()
    ]
    symbols = [item.upper() for item in (args.symbols or configured)]
    for symbol in symbols:
        initial, current = await backfill_market(
            symbol,
            args.interval,
            args.target_per_market,
            args.batch_size,
        )
        print(
            f"{symbol} {args.interval}: concluído com {current} candles "
            f"(+{current - initial})"
        )


if __name__ == "__main__":
    asyncio.run(main())
