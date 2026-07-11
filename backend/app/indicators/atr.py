from collections.abc import Iterable
from decimal import Decimal

from app.indicators.utils import (
    as_decimals,
    validate_period,
    validate_same_length,
)


def calculate_true_ranges(
    highs: Iterable[Decimal | int | float | str],
    lows: Iterable[Decimal | int | float | str],
    closes: Iterable[Decimal | int | float | str],
) -> list[Decimal]:
    high_values = as_decimals(highs)
    low_values = as_decimals(lows)
    close_values = as_decimals(closes)
    validate_same_length(high_values, low_values, close_values)

    result = [high_values[0] - low_values[0]]
    for index in range(1, len(close_values)):
        result.append(
            max(
                high_values[index] - low_values[index],
                abs(high_values[index] - close_values[index - 1]),
                abs(low_values[index] - close_values[index - 1]),
            )
        )
    return result


def calculate_atr(
    highs: Iterable[Decimal | int | float | str],
    lows: Iterable[Decimal | int | float | str],
    closes: Iterable[Decimal | int | float | str],
    period: int = 14,
) -> list[Decimal | None]:
    validate_period(period)
    true_ranges = calculate_true_ranges(highs, lows, closes)
    result: list[Decimal | None] = [None] * len(true_ranges)
    if len(true_ranges) < period:
        return result

    current = sum(true_ranges[:period], Decimal(0)) / Decimal(period)
    result[period - 1] = current
    for index in range(period, len(true_ranges)):
        current = (
            current * Decimal(period - 1) + true_ranges[index]
        ) / Decimal(period)
        result[index] = current
    return result
