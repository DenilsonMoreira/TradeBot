import logging
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Protocol

from app.models.candle import Candle
from app.repositories.candle_repository import CandleRepository


logger = logging.getLogger(__name__)


class CandleClient(Protocol):
    async def get_candles(
        self,
        symbol: str,
        interval: str = "15m",
        limit: int = 100,
        start_time: int | None = None,
    ) -> list: ...


class CandleService:
    def __init__(
        self,
        repository: CandleRepository,
        client: CandleClient,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self.client = client
        self.now = now or (lambda: datetime.now(UTC))

    def normalize_candle(
        self,
        symbol: str,
        interval: str,
        payload: Sequence[object],
    ) -> Candle:
        if len(payload) < 11:
            raise ValueError("Payload de candle da Binance incompleto")

        try:
            open_time = self._from_milliseconds(payload[0])
            close_time = self._from_milliseconds(payload[6])
            return Candle(
                symbol=symbol.upper(),
                interval=interval,
                open_time=open_time,
                close_time=close_time,
                open=Decimal(str(payload[1])),
                high=Decimal(str(payload[2])),
                low=Decimal(str(payload[3])),
                close=Decimal(str(payload[4])),
                volume=Decimal(str(payload[5])),
                quote_volume=Decimal(str(payload[7])),
                trades=int(payload[8]),
                taker_buy_volume=Decimal(str(payload[9])),
                taker_buy_quote=Decimal(str(payload[10])),
                is_closed=close_time < self._utc_now(),
            )
        except (InvalidOperation, TypeError, ValueError, OverflowError) as error:
            raise ValueError("Payload de candle da Binance inválido") from error

    def get_history(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
        offset: int = 0,
        closed_only: bool = True,
    ) -> Sequence[Candle]:
        return self.repository.get_history(
            symbol,
            interval,
            limit=limit,
            offset=offset,
            closed_only=closed_only,
        )

    def get_latest(
        self,
        symbol: str,
        interval: str,
        *,
        closed_only: bool = False,
    ) -> Candle | None:
        return self.repository.get_latest(
            symbol,
            interval,
            closed_only=closed_only,
        )

    async def sync_history(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
    ) -> list[Candle]:
        self._validate_limit(limit)
        normalized_symbol = symbol.upper()
        payloads = await self.client.get_candles(
            normalized_symbol,
            interval,
            limit,
        )
        return self._persist(
            normalized_symbol,
            interval,
            payloads,
        )

    async def sync_incremental(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
    ) -> list[Candle]:
        self._validate_limit(limit)
        normalized_symbol = symbol.upper()
        latest = self.repository.get_latest(normalized_symbol, interval)

        if latest is None:
            return await self.sync_history(
                normalized_symbol,
                interval,
                limit=limit,
            )

        start_time = self._to_milliseconds(latest.open_time)
        if latest.is_closed:
            start_time += 1

        payloads = await self.client.get_candles(
            normalized_symbol,
            interval,
            limit,
            start_time=start_time,
        )
        return self._persist(
            normalized_symbol,
            interval,
            payloads,
        )

    def _persist(
        self,
        symbol: str,
        interval: str,
        payloads: Sequence[Sequence[object]],
    ) -> list[Candle]:
        candles = [
            self.normalize_candle(symbol, interval, payload)
            for payload in payloads
        ]
        if not candles:
            return []

        try:
            persisted = self.repository.upsert_many(candles)
            self.repository.session.commit()
        except Exception:
            self.repository.session.rollback()
            logger.exception(
                "Falha ao persistir candles",
                extra={
                    "symbol": symbol,
                    "interval": interval,
                    "candle_count": len(candles),
                },
            )
            raise

        logger.info(
            "Candles sincronizados",
            extra={
                "symbol": symbol,
                "interval": interval,
                "candle_count": len(persisted),
            },
        )
        return persisted

    def _utc_now(self) -> datetime:
        current = self.now()
        if current.tzinfo is None:
            raise ValueError("O relógio do CandleService deve possuir timezone")
        return current.astimezone(UTC)

    @staticmethod
    def _from_milliseconds(value: object) -> datetime:
        return datetime.fromtimestamp(int(value) / 1000, tz=UTC)

    @staticmethod
    def _to_milliseconds(value: datetime) -> int:
        if value.tzinfo is None:
            raise ValueError("open_time deve possuir timezone")
        return int(value.timestamp() * 1000)

    @staticmethod
    def _validate_limit(limit: int) -> None:
        if not 1 <= limit <= 1000:
            raise ValueError("limit deve estar entre 1 e 1000")
