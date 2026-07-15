from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.candle import Candle


class CandleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save(self, candle: Candle) -> Candle:
        self.session.add(candle)
        self.session.flush()
        return candle

    def save_many(self, candles: Iterable[Candle]) -> list[Candle]:
        items = list(candles)
        if not items:
            return []

        self.session.add_all(items)
        self.session.flush()
        return items

    def upsert_many(
        self,
        candles: Iterable[Candle | dict[str, Any]],
    ) -> list[Candle]:
        values = [self._as_values(candle) for candle in candles]
        if not values:
            return []

        statement = insert(Candle).values(values)
        excluded = statement.excluded
        statement = statement.on_conflict_do_update(
            constraint="uq_candles_symbol_interval_open_time",
            set_={
                "close_time": excluded.close_time,
                "open": excluded.open,
                "high": excluded.high,
                "low": excluded.low,
                "close": excluded.close,
                "volume": excluded.volume,
                "quote_volume": excluded.quote_volume,
                "trades": excluded.trades,
                "taker_buy_volume": excluded.taker_buy_volume,
                "taker_buy_quote": excluded.taker_buy_quote,
                "is_closed": excluded.is_closed,
            },
        ).returning(Candle)

        return list(
            self.session.scalars(
                statement,
                execution_options={"populate_existing": True},
            ).all()
        )

    def get_latest(
        self,
        symbol: str,
        interval: str,
        *,
        closed_only: bool = False,
    ) -> Candle | None:
        statement = self._history_statement(
            symbol=symbol,
            interval=interval,
            closed_only=closed_only,
        ).limit(1)
        return self.session.scalar(statement)

    def get_history(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
        offset: int = 0,
        closed_only: bool = True,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> Sequence[Candle]:
        if limit < 1:
            raise ValueError("limit deve ser maior que zero")
        if offset < 0:
            raise ValueError("offset não pode ser negativo")

        statement = self._history_statement(
            symbol=symbol,
            interval=interval,
            closed_only=closed_only,
        )
        if start_time is not None:
            statement = statement.where(Candle.open_time >= start_time)
        if end_time is not None:
            statement = statement.where(Candle.open_time <= end_time)

        return self.session.scalars(
            statement.offset(offset).limit(limit)
        ).all()

    def get_last_open_time(
        self,
        symbol: str,
        interval: str,
    ) -> datetime | None:
        statement = select(func.max(Candle.open_time)).where(
            Candle.symbol == symbol.upper(),
            Candle.interval == interval,
        )
        return self.session.scalar(statement)

    def get_first_open_time(
        self,
        symbol: str,
        interval: str,
    ) -> datetime | None:
        statement = select(func.min(Candle.open_time)).where(
            Candle.symbol == symbol.upper(),
            Candle.interval == interval,
        )
        return self.session.scalar(statement)

    def count(self, symbol: str, interval: str) -> int:
        statement = select(func.count(Candle.id)).where(
            Candle.symbol == symbol.upper(),
            Candle.interval == interval,
        )
        return int(self.session.scalar(statement) or 0)

    def exists(
        self,
        symbol: str,
        interval: str,
        open_time: datetime,
    ) -> bool:
        statement = select(
            select(Candle.id)
            .where(
                Candle.symbol == symbol.upper(),
                Candle.interval == interval,
                Candle.open_time == open_time,
            )
            .exists()
        )
        return bool(self.session.scalar(statement))

    @staticmethod
    def _as_values(candle: Candle | dict[str, Any]) -> dict[str, Any]:
        if isinstance(candle, dict):
            values = dict(candle)
        else:
            values = {
                column.name: getattr(candle, column.name)
                for column in Candle.__table__.columns
                if column.name not in {"id", "created_at"}
            }

        values.pop("id", None)
        values.pop("created_at", None)
        values["symbol"] = values["symbol"].upper()
        return values

    @staticmethod
    def _history_statement(
        symbol: str,
        interval: str,
        closed_only: bool,
    ) -> Select[tuple[Candle]]:
        statement = select(Candle).where(
            Candle.symbol == symbol.upper(),
            Candle.interval == interval,
        )
        if closed_only:
            statement = statement.where(Candle.is_closed.is_(True))
        return statement.order_by(Candle.open_time.desc())
