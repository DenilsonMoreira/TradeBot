from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.candle import Candle
from app.models.indicator import Indicator


class IndicatorRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_many(
        self,
        indicators: Iterable[Indicator | dict[str, Any]],
    ) -> list[Indicator]:
        values = [self._as_values(indicator) for indicator in indicators]
        if not values:
            return []

        statement = insert(Indicator).values(values)
        excluded = statement.excluded
        statement = statement.on_conflict_do_update(
            constraint="uq_indicators_candle_name_config_version",
            set_={
                "parameters": excluded.parameters,
                "value": excluded.value,
            },
        ).returning(Indicator)
        return list(
            self.session.scalars(
                statement,
                execution_options={"populate_existing": True},
            ).all()
        )

    def get_existing_keys(
        self,
        candle_ids: Iterable[int],
        config_version: str,
    ) -> set[tuple[int, str]]:
        ids = list(candle_ids)
        if not ids:
            return set()
        statement = select(Indicator.candle_id, Indicator.name).where(
            Indicator.candle_id.in_(ids),
            Indicator.config_version == config_version,
        )
        return set(self.session.execute(statement).tuples().all())

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
        if limit < 1:
            raise ValueError("limit deve ser maior que zero")
        if offset < 0:
            raise ValueError("offset não pode ser negativo")

        statement = (
            select(Indicator)
            .join(Candle, Candle.id == Indicator.candle_id)
            .where(
                Candle.symbol == symbol.upper(),
                Candle.interval == interval,
            )
        )
        if name:
            statement = statement.where(Indicator.name == name.upper())
        if config_version:
            statement = statement.where(
                Indicator.config_version == config_version
            )
        statement = statement.order_by(
            Candle.open_time.desc(),
            Indicator.name.asc(),
        )
        return self.session.scalars(
            statement.offset(offset).limit(limit)
        ).all()

    @staticmethod
    def _as_values(
        indicator: Indicator | dict[str, Any],
    ) -> dict[str, Any]:
        if isinstance(indicator, dict):
            values = dict(indicator)
        else:
            values = {
                "candle_id": indicator.candle_id,
                "name": indicator.name,
                "config_version": indicator.config_version,
                "parameters": indicator.parameters,
                "value": indicator.value,
            }
        values.pop("id", None)
        values.pop("created_at", None)
        values["name"] = values["name"].upper()
        return values
