from collections.abc import Iterable, Sequence
from decimal import Decimal


def as_decimals(values: Iterable[Decimal | int | float | str]) -> list[Decimal]:
    return [
        value if isinstance(value, Decimal) else Decimal(str(value))
        for value in values
    ]


def validate_period(period: int) -> None:
    if period < 1:
        raise ValueError("period deve ser maior que zero")


def validate_same_length(*series: Sequence[object]) -> None:
    if not series or not series[0]:
        raise ValueError("as séries não podem estar vazias")
    expected = len(series[0])
    if any(len(values) != expected for values in series[1:]):
        raise ValueError("as séries devem possuir o mesmo tamanho")
