from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_indicator_service, get_operator_session, require_operator_csrf
from app.schemas.indicator import (
    IndicatorCalculateRequest,
    IndicatorCalculateResponse,
    IndicatorResponse,
)
from app.services.indicator_service import IndicatorService


router = APIRouter(prefix="/indicators", tags=["indicators"])


@router.get("", response_model=list[IndicatorResponse], dependencies=[Depends(get_operator_session)])
def get_indicators(
    symbol: str = Query(min_length=5, max_length=20),
    interval: str = Query(min_length=2, max_length=10),
    name: str | None = Query(default=None, max_length=32),
    config_version: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=500, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: IndicatorService = Depends(get_indicator_service),
):
    return service.get_history(
        symbol,
        interval,
        name=name,
        config_version=config_version,
        limit=limit,
        offset=offset,
    )


@router.post("/calculate", response_model=IndicatorCalculateResponse, dependencies=[Depends(require_operator_csrf)])
def calculate_indicators(
    payload: IndicatorCalculateRequest,
    service: IndicatorService = Depends(get_indicator_service),
):
    indicators = service.calculate_and_persist(
        payload.symbol,
        payload.interval,
    )
    return IndicatorCalculateResponse(
        symbol=payload.symbol,
        interval=payload.interval,
        config_version=service.config_version,
        persisted=len(indicators),
    )
