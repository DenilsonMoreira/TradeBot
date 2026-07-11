from collections.abc import Iterable
from decimal import Decimal

from app.indicators.utils import as_decimals, validate_period


def calculate_ema(
    values: Iterable[Decimal | int | float | str],
    period: int,
) -> list[Decimal]:
    validate_period(period)
    items = as_decimals(values)
    if not items:
        return []

    multiplier = Decimal(2) / Decimal(period + 1)
    result = [items[0]]
    for value in items[1:]:
        result.append((value - result[-1]) * multiplier + result[-1])
    return result
