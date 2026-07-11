from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_backtest_service, get_dataset_service, get_ensemble_service, get_model_registry, get_operator_session, get_prediction_service, get_research_repository, get_training_service, require_operator_csrf
from app.ai.registry import ModelRegistry
from app.backtest.engine import BacktestConfig
from app.repositories.research_repository import ResearchRepository
from app.schemas.research import BacktestRequest, BacktestResponse, DatasetRequest, DatasetResponse, EnsembleRequest, ModelResponse, PredictionRequest, PredictionResponse, TrainingRequest
from app.services.ensemble_service import EnsembleService
from app.services.prediction_service import PredictionService
from app.services.backtest_service import BacktestService
from app.services.dataset_service import DatasetService
from app.services.training_service import TrainingService


router = APIRouter(tags=["research"])


@router.post("/backtests/run", response_model=BacktestResponse, dependencies=[Depends(require_operator_csrf)])
def run_backtest(payload: BacktestRequest, service: BacktestService = Depends(get_backtest_service)):
    try:
        return service.run(payload.symbol, payload.interval, BacktestConfig(payload.initial_capital, payload.fee_rate, payload.slippage_rate), payload.limit)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@router.get("/backtests", response_model=list[BacktestResponse], dependencies=[Depends(get_operator_session)])
def list_backtests(limit: int = Query(50, ge=1, le=200), repository: ResearchRepository = Depends(get_research_repository)):
    return repository.list_backtests(limit)


@router.post("/datasets/build", response_model=DatasetResponse, dependencies=[Depends(require_operator_csrf)])
def build_dataset(payload: DatasetRequest, service: DatasetService = Depends(get_dataset_service)):
    try:
        return service.build(payload.symbol, payload.interval, payload.limit, payload.horizon, payload.train_ratio)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@router.get("/datasets", response_model=list[DatasetResponse], dependencies=[Depends(get_operator_session)])
def list_datasets(limit: int = Query(50, ge=1, le=200), repository: ResearchRepository = Depends(get_research_repository)):
    return repository.list_datasets(limit)


@router.post("/models/train", response_model=list[ModelResponse], dependencies=[Depends(require_operator_csrf)])
def train_models(payload: TrainingRequest, service: TrainingService = Depends(get_training_service)):
    try:
        return service.train(payload.dataset_id)
    except ValueError as error:
        raise HTTPException(404, str(error)) from error


@router.get("/models", response_model=list[ModelResponse], dependencies=[Depends(get_operator_session)])
def list_models(limit: int = Query(50, ge=1, le=200), repository: ResearchRepository = Depends(get_research_repository)):
    return repository.list_models(limit)


@router.post("/models/{model_id}/promote", response_model=ModelResponse, dependencies=[Depends(require_operator_csrf)])
def promote_model(
    model_id: int,
    registry: ModelRegistry = Depends(get_model_registry),
):
    try:
        return registry.promote(model_id)
    except ValueError as error:
        raise HTTPException(404, str(error)) from error


@router.post("/models/{model_id}/deactivate", response_model=ModelResponse, dependencies=[Depends(require_operator_csrf)])
def deactivate_model(
    model_id: int,
    registry: ModelRegistry = Depends(get_model_registry),
):
    try:
        return registry.deactivate(model_id)
    except ValueError as error:
        raise HTTPException(404, str(error)) from error


@router.get("/datasets/{dataset_id}/models/active", response_model=ModelResponse | None, dependencies=[Depends(get_operator_session)])
def get_active_model(
    dataset_id: int,
    registry: ModelRegistry = Depends(get_model_registry),
):
    return registry.get_active(dataset_id)


@router.post("/ensembles/evaluate", response_model=ModelResponse, dependencies=[Depends(require_operator_csrf)])
def evaluate_ensemble(
    payload: EnsembleRequest,
    service: EnsembleService = Depends(get_ensemble_service),
):
    try:
        return service.evaluate(
            payload.dataset_id,
            model_ids=payload.model_ids,
            threshold=payload.threshold,
        )
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@router.get("/datasets/{dataset_id}/models/recommend", response_model=ModelResponse | None, dependencies=[Depends(get_operator_session)])
def recommend_model(
    dataset_id: int,
    min_strategy_return: float = Query(default=0.0),
    min_f1: float = Query(default=0.0, ge=0, le=1),
    registry: ModelRegistry = Depends(get_model_registry),
):
    return registry.recommend(
        dataset_id,
        min_strategy_return=min_strategy_return,
        min_f1=min_f1,
    )


@router.post("/predictions", response_model=PredictionResponse, dependencies=[Depends(require_operator_csrf)])
def create_prediction(
    payload: PredictionRequest,
    service: PredictionService = Depends(get_prediction_service),
):
    try:
        return service.predict(
            payload.dataset_id,
            payload.candle_id,
            payload.features,
        )
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@router.get("/datasets/{dataset_id}/predictions", response_model=list[PredictionResponse], dependencies=[Depends(get_operator_session)])
def list_predictions(
    dataset_id: int,
    limit: int = Query(default=100, ge=1, le=1000),
    repository: ResearchRepository = Depends(get_research_repository),
):
    return repository.list_predictions(dataset_id, limit)
