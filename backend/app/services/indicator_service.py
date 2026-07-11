import logging
from collections.abc import Sequence
from decimal import Decimal

from app.indicators import (
    calculate_adx,
    calculate_atr,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
)
from app.models.candle import Candle
from app.models.indicator import Indicator
from app.repositories.candle_repository import CandleRepository
from app.repositories.indicator_repository import IndicatorRepository


logger = logging.getLogger(__name__)
INDICATOR_NAMES = {
    "EMA_9",
    "EMA_21",
    "RSI_14",
    "MACD",
    "MACD_SIGNAL",
    "MACD_HISTOGRAM",
    "ATR_14",
    "ADX_14",
}


class IndicatorService:
    def __init__(
        self,
        candle_repository: CandleRepository,
        indicator_repository: IndicatorRepository,
        *,
        history_limit: int = 1000,
    ) -> None:
        if history_limit < 50:
            raise ValueError("history_limit deve ser no mínimo 50")
        self.candle_repository = candle_repository
        self.indicator_repository = indicator_repository
        self.history_limit = history_limit
        self.config_version = f"technical-v1-h{history_limit}"

    def calculate_and_persist(
        self,
        symbol: str,
        interval: str,
    ) -> list[Indicator]:
        candles = list(
            reversed(
                self.candle_repository.get_history(
                    symbol,
                    interval,
                    limit=self.history_limit,
                    closed_only=True,
                )
            )
        )
        if not candles:
            return []

        existing = self.indicator_repository.get_existing_keys(
            (candle.id for candle in candles),
            self.config_version,
        )
        latest_id = candles[-1].id
        if all((latest_id, name) in existing for name in INDICATOR_NAMES):
            return []

        pending = self._calculate(candles, existing)
        if not pending:
            return []

        try:
            persisted = self.indicator_repository.upsert_many(pending)
            self.indicator_repository.session.commit()
        except Exception:
            self.indicator_repository.session.rollback()
            logger.exception(
                "Falha ao persistir indicadores",
                extra={
                    "symbol": symbol.upper(),
                    "interval": interval,
                    "indicator_count": len(pending),
                    "config_version": self.config_version,
                },
            )
            raise

        logger.info(
            "Indicadores persistidos",
            extra={
                "symbol": symbol.upper(),
                "interval": interval,
                "indicator_count": len(persisted),
                "config_version": self.config_version,
            },
        )
        return persisted

    def get_history(
        self,
        symbol: str,
        interval: str,
        *,
        name: str | None = None,
        config_version: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> Sequence[Indicator]:
        return self.indicator_repository.get_history(
            symbol,
            interval,
            name=name,
            config_version=config_version,
            limit=limit,
            offset=offset,
        )

    def _calculate(
        self,
        candles: Sequence[Candle],
        existing: set[tuple[int, str]],
    ) -> list[Indicator]:
        closes = [candle.close for candle in candles]
        highs = [candle.high for candle in candles]
        lows = [candle.low for candle in candles]
        ema_9 = calculate_ema(closes, 9)
        ema_21 = calculate_ema(closes, 21)
        rsi_14 = calculate_rsi(closes, 14)
        macd = calculate_macd(closes, 12, 26, 9)
        atr_14 = calculate_atr(highs, lows, closes, 14)
        adx_14 = calculate_adx(highs, lows, closes, 14)

        pending: list[Indicator] = []
        for index, candle in enumerate(candles):
            values = {
                "EMA_9": (ema_9[index], {"period": 9}),
                "EMA_21": (ema_21[index], {"period": 21}),
                "RSI_14": (rsi_14[index], {"period": 14}),
                "MACD": (
                    macd[index].macd,
                    {"fast": 12, "slow": 26, "signal": 9},
                ),
                "MACD_SIGNAL": (
                    macd[index].signal,
                    {"fast": 12, "slow": 26, "signal": 9},
                ),
                "MACD_HISTOGRAM": (
                    macd[index].histogram,
                    {"fast": 12, "slow": 26, "signal": 9},
                ),
                "ATR_14": (atr_14[index], {"period": 14}),
                "ADX_14": (adx_14[index], {"period": 14}),
            }
            for name, (value, parameters) in values.items():
                if value is None or (candle.id, name) in existing:
                    continue
                pending.append(
                    Indicator(
                        candle_id=candle.id,
                        name=name,
                        config_version=self.config_version,
                        parameters={
                            **parameters,
                            "history_limit": self.history_limit,
                        },
                        value=Decimal(value),
                    )
                )
        return pending
