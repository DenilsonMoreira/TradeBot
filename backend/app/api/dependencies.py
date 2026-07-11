from fastapi import Depends
from sqlalchemy.orm import Session

from app.binance.client import BinanceTestnetClient
from app.database import get_db
from app.repositories.candle_repository import CandleRepository
from app.services.candle_service import CandleService
from app.config import settings
from app.repositories.indicator_repository import IndicatorRepository
from app.services.indicator_service import IndicatorService


def get_candle_service(db: Session = Depends(get_db)) -> CandleService:
    return CandleService(CandleRepository(db), BinanceTestnetClient())


def get_indicator_service(db: Session = Depends(get_db)) -> IndicatorService:
    return IndicatorService(
        CandleRepository(db),
        IndicatorRepository(db),
        history_limit=settings.indicator_history_limit,
    )
