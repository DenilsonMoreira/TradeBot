from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_backtest_service, get_dataset_service, get_research_repository, get_training_service
from app.backtest.engine import BacktestConfig
from app.repositories.research_repository import ResearchRepository
from app.schemas.research import BacktestRequest, BacktestResponse, DatasetRequest, DatasetResponse, ModelResponse, TrainingRequest
from app.services.backtest_service import BacktestService
from app.services.dataset_service import DatasetService
from app.services.training_service import TrainingService


router = APIRouter(tags=["research"])


@router.post("/backtests/run", response_model=BacktestResponse)
def run_backtest(payload: BacktestRequest, service: BacktestService = Depends(get_backtest_service)):
    try:
        return service.run(payload.symbol, payload.interval, BacktestConfig(payload.initial_capital, payload.fee_rate, payload.slippage_rate), payload.limit)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@router.get("/backtests", response_model=list[BacktestResponse])
def list_backtests(limit: int = Query(50, ge=1, le=200), repository: ResearchRepository = Depends(get_research_repository)):
    return repository.list_backtests(limit)


@router.post("/datasets/build", response_model=DatasetResponse)
def build_dataset(payload: DatasetRequest, service: DatasetService = Depends(get_dataset_service)):
    try:
        return service.build(payload.symbol, payload.interval, payload.limit, payload.horizon, payload.train_ratio)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@router.get("/datasets", response_model=list[DatasetResponse])
def list_datasets(limit: int = Query(50, ge=1, le=200), repository: ResearchRepository = Depends(get_research_repository)):
    return repository.list_datasets(limit)


@router.post("/models/train", response_model=list[ModelResponse])
def train_models(payload: TrainingRequest, service: TrainingService = Depends(get_training_service)):
    try:
        return service.train(payload.dataset_id)
    except ValueError as error:
        raise HTTPException(404, str(error)) from error


@router.get("/models", response_model=list[ModelResponse])
def list_models(limit: int = Query(50, ge=1, le=200), repository: ResearchRepository = Depends(get_research_repository)):
    return repository.list_models(limit)
