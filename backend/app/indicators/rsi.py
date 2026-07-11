from collections.abc import Iterable
from decimal import Decimal

from app.indicators.utils import as_decimals, validate_period


def calculate_rsi(
    closes: Iterable[Decimal | int | float | str],
    period: int = 14,
) -> list[Decimal | None]:
    validate_period(period)
    values = as_decimals(closes)
    result: list[Decimal | None] = [None] * len(values)
    if len(values) <= period:
        return result

    changes = [
        values[index] - values[index - 1]
        for index in range(1, len(values))
    ]
    gains = [max(change, Decimal(0)) for change in changes]
    losses = [max(-change, Decimal(0)) for change in changes]
    average_gain = sum(gains[:period], Decimal(0)) / Decimal(period)
    average_loss = sum(losses[:period], Decimal(0)) / Decimal(period)
    result[period] = _rsi_value(average_gain, average_loss)

    for index in range(period, len(changes)):
        average_gain = (
            average_gain * Decimal(period - 1) + gains[index]
        ) / Decimal(period)
        average_loss = (
            average_loss * Decimal(period - 1) + losses[index]
        ) / Decimal(period)
        result[index + 1] = _rsi_value(average_gain, average_loss)
    return result


def _rsi_value(average_gain: Decimal, average_loss: Decimal) -> Decimal:
    if average_loss == 0:
        return Decimal(100) if average_gain > 0 else Decimal(50)
    relative_strength = average_gain / average_loss
    return Decimal(100) - Decimal(100) / (Decimal(1) + relative_strength)
