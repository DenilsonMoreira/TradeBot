import hmac

from fastapi import Depends, HTTPException, Request, status
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
from app.ai.registry import ModelRegistry
from app.services.ensemble_service import EnsembleService
from app.services.prediction_service import PredictionService
from app.api.routes.auth import COOKIE_NAME, auth_is_configured
from app.core.security import OperatorSession, read_session


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


def get_model_registry(db: Session = Depends(get_db)) -> ModelRegistry:
    return ModelRegistry(ResearchRepository(db))


def get_ensemble_service(db: Session = Depends(get_db)) -> EnsembleService:
    return EnsembleService(ResearchRepository(db), settings.model_artifact_dir)


def get_prediction_service(db: Session = Depends(get_db)) -> PredictionService:
    return PredictionService(ResearchRepository(db))


def get_operator_session(request: Request) -> OperatorSession:
    if not auth_is_configured():
        raise HTTPException(status_code=503, detail="Autenticação do operador não configurada.")
    authorization = request.headers.get("Authorization", "")
    bearer = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    token = bearer or request.cookies.get(COOKIE_NAME, "")
    session = read_session(token, settings.auth_secret_key)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão ausente ou expirada.")
    return session


def require_operator_csrf(
    request: Request,
    session: OperatorSession = Depends(get_operator_session),
) -> OperatorSession:
    csrf = request.headers.get("X-CSRF-Token", "")
    if not hmac.compare_digest(csrf, session.csrf_token):
        raise HTTPException(status_code=403, detail="Token CSRF inválido.")
    return session
