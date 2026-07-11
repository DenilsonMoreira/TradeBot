from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from app.indicators.ema import calculate_ema
from app.indicators.utils import as_decimals, validate_period


@dataclass(frozen=True)
class MacdPoint:
    macd: Decimal
    signal: Decimal
    histogram: Decimal


def calculate_macd(
    closes: Iterable[Decimal | int | float | str],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> list[MacdPoint]:
    validate_period(fast_period)
    validate_period(slow_period)
    validate_period(signal_period)
    if fast_period >= slow_period:
        raise ValueError("fast_period deve ser menor que slow_period")

    values = as_decimals(closes)
    if not values:
        return []
    fast = calculate_ema(values, fast_period)
    slow = calculate_ema(values, slow_period)
    macd_values = [
        fast_value - slow_value
        for fast_value, slow_value in zip(fast, slow)
    ]
    signal_values = calculate_ema(macd_values, signal_period)
    return [
        MacdPoint(macd=value, signal=signal, histogram=value - signal)
        for value, signal in zip(macd_values, signal_values)
    ]
