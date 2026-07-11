from sqlalchemy import BigInteger, DateTime, Numeric, UniqueConstraint

from app.models.candle import Candle


def test_candle_model_uses_financial_and_timezone_aware_types() -> None:
    table = Candle.__table__

    assert isinstance(table.c.id.type, BigInteger)
    for name in (
        "open",
        "high",
        "low",
        "close",
        "volume",
        "quote_volume",
        "taker_buy_volume",
        "taker_buy_quote",
    ):
        assert isinstance(table.c[name].type, Numeric)

    assert isinstance(table.c.open_time.type, DateTime)
    assert table.c.open_time.type.timezone is True
    assert table.c.close_time.type.timezone is True
    assert table.c.created_at.type.timezone is True


def test_candle_model_has_idempotency_constraint() -> None:
    constraints = [
        constraint
        for constraint in Candle.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    ]

    assert any(
        constraint.name == "uq_candles_symbol_interval_open_time"
        and tuple(column.name for column in constraint.columns)
        == ("symbol", "interval", "open_time")
        for constraint in constraints
    )
