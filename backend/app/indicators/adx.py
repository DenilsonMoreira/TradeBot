from collections.abc import Iterable
from decimal import Decimal

from app.indicators.atr import calculate_true_ranges
from app.indicators.utils import (
    as_decimals,
    validate_period,
    validate_same_length,
)


def calculate_adx(
    highs: Iterable[Decimal | int | float | str],
    lows: Iterable[Decimal | int | float | str],
    closes: Iterable[Decimal | int | float | str],
    period: int = 14,
) -> list[Decimal | None]:
    validate_period(period)
    high_values = as_decimals(highs)
    low_values = as_decimals(lows)
    close_values = as_decimals(closes)
    validate_same_length(high_values, low_values, close_values)
    size = len(close_values)
    result: list[Decimal | None] = [None] * size
    if size < period * 2:
        return result

    true_ranges = calculate_true_ranges(high_values, low_values, close_values)
    plus_dm = [Decimal(0)] * size
    minus_dm = [Decimal(0)] * size
    for index in range(1, size):
        up_move = high_values[index] - high_values[index - 1]
        down_move = low_values[index - 1] - low_values[index]
        if up_move > down_move and up_move > 0:
            plus_dm[index] = up_move
        if down_move > up_move and down_move > 0:
            minus_dm[index] = down_move

    atr = sum(true_ranges[1 : period + 1], Decimal(0)) / Decimal(period)
    smooth_plus = sum(plus_dm[1 : period + 1], Decimal(0)) / Decimal(period)
    smooth_minus = sum(minus_dm[1 : period + 1], Decimal(0)) / Decimal(period)
    dx_values: list[Decimal] = []

    for index in range(period, size):
        if index > period:
            atr = (
                atr * Decimal(period - 1) + true_ranges[index]
            ) / Decimal(period)
            smooth_plus = (
                smooth_plus * Decimal(period - 1) + plus_dm[index]
            ) / Decimal(period)
            smooth_minus = (
                smooth_minus * Decimal(period - 1) + minus_dm[index]
            ) / Decimal(period)
        plus_di = Decimal(0) if atr == 0 else Decimal(100) * smooth_plus / atr
        minus_di = Decimal(0) if atr == 0 else Decimal(100) * smooth_minus / atr
        denominator = plus_di + minus_di
        dx_values.append(
            Decimal(0)
            if denominator == 0
            else Decimal(100) * abs(plus_di - minus_di) / denominator
        )

    adx = sum(dx_values[:period], Decimal(0)) / Decimal(period)
    first_index = period * 2 - 1
    result[first_index] = adx
    for dx_index in range(period, len(dx_values)):
        adx = (
            adx * Decimal(period - 1) + dx_values[dx_index]
        ) / Decimal(period)
        result[period + dx_index] = adx
    return result
