from fastapi import Depends
from sqlalchemy.orm import Session

from app.binance.client import BinanceTestnetClient
from app.database import get_db
from app.repositories.candle_repository import CandleRepository
from app.services.candle_service import CandleService


def get_candle_service(db: Session = Depends(get_db)) -> CandleService:
    return CandleService(CandleRepository(db), BinanceTestnetClient())
