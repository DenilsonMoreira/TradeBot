from sqlalchemy import DateTime, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app.models.indicator import Indicator


def test_indicator_model_uses_precise_versioned_values() -> None:
    table = Indicator.__table__

    assert isinstance(table.c.value.type, Numeric)
    assert isinstance(table.c.parameters.type, JSONB)
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True


def test_indicator_model_has_idempotency_constraint() -> None:
    constraints = [
        constraint
        for constraint in Indicator.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    ]

    assert any(
        constraint.name == "uq_indicators_candle_name_config_version"
        and tuple(column.name for column in constraint.columns)
        == ("candle_id", "name", "config_version")
        for constraint in constraints
    )
