from fastapi import Depends
from sqlalchemy.orm import Session

from app.binance.client import BinanceTestnetClient
from app.database import get_db
from app.repositories.candle_repository import CandleRepository
from app.services.candle_service import CandleService
from app.config import settings
from app.repositories.indicator_repository import IndicatorRepository
from app.services.indicator_service import IndicatorService
from app.repositories.research_repository import ResearchRepository
from app.services.backtest_service import BacktestService
from app.services.dataset_service import DatasetService
from app.services.training_service import TrainingService


def get_candle_service(db: Session = Depends(get_db)) -> CandleService:
    return CandleService(CandleRepository(db), BinanceTestnetClient())


def get_indicator_service(db: Session = Depends(get_db)) -> IndicatorService:
    return IndicatorService(
        CandleRepository(db),
        IndicatorRepository(db),
        history_limit=settings.indicator_history_limit,
    )


def get_research_repository(db: Session = Depends(get_db)) -> ResearchRepository:
    return ResearchRepository(db)


def get_backtest_service(db: Session = Depends(get_db)) -> BacktestService:
    return BacktestService(CandleRepository(db), ResearchRepository(db))


def get_dataset_service(db: Session = Depends(get_db)) -> DatasetService:
    return DatasetService(CandleRepository(db), ResearchRepository(db))


def get_training_service(db: Session = Depends(get_db)) -> TrainingService:
    return TrainingService(ResearchRepository(db), settings.model_artifact_dir)
