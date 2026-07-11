from decimal import Decimal

import pytest

from app.indicators import (
    calculate_adx,
    calculate_atr,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
)


def test_ema_uses_standard_recursive_smoothing() -> None:
    result = calculate_ema([1, 2, 3], period=2)

    assert result[0] == Decimal(1)
    assert result[1].quantize(Decimal("0.000001")) == Decimal("1.666667")
    assert result[2].quantize(Decimal("0.000001")) == Decimal("2.555556")


def test_rsi_wilder_for_rising_and_constant_series() -> None:
    rising = calculate_rsi(range(1, 17), period=14)
    constant = calculate_rsi([10] * 16, period=14)

    assert rising[:14] == [None] * 14
    assert rising[14:] == [Decimal(100), Decimal(100)]
    assert constant[14:] == [Decimal(50), Decimal(50)]


def test_macd_is_zero_for_constant_prices() -> None:
    result = calculate_macd([Decimal("42.5")] * 30)

    assert all(point.macd == 0 for point in result)
    assert all(point.signal == 0 for point in result)
    assert all(point.histogram == 0 for point in result)


def test_atr_is_range_for_constant_ohlc_ranges() -> None:
    result = calculate_atr([11] * 20, [9] * 20, [10] * 20, period=14)

    assert result[:13] == [None] * 13
    assert result[13:] == [Decimal(2)] * 7


def test_adx_reaches_100_for_strong_unidirectional_trend() -> None:
    highs = list(range(11, 51))
    lows = list(range(9, 49))
    closes = list(range(10, 50))

    result = calculate_adx(highs, lows, closes, period=14)

    assert result[:27] == [None] * 27
    assert result[27:] == [Decimal(100)] * 13


def test_indicators_validate_parameters_and_lengths() -> None:
    with pytest.raises(ValueError, match="period"):
        calculate_ema([1, 2], period=0)
    with pytest.raises(ValueError, match="menor"):
        calculate_macd([1, 2], fast_period=26, slow_period=12)
    with pytest.raises(ValueError, match="mesmo tamanho"):
        calculate_atr([1, 2], [1], [1, 2])
