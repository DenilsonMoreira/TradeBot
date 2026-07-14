import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.dependencies import get_candle_service, get_operator_session, require_operator_csrf
from app.schemas.candle import (
    CandleResponse,
    CandleSyncRequest,
    CandleSyncResponse,
    MarketConfigResponse,
)
from app.services.candle_service import CandleService
from app.config import settings


router = APIRouter(prefix="/candles", tags=["candles"])


@router.get("/config", response_model=MarketConfigResponse, dependencies=[Depends(get_operator_session)])
def get_market_config() -> MarketConfigResponse:
    symbols = list(dict.fromkeys(symbol.strip().upper() for symbol in settings.candle_symbols.split(",") if symbol.strip()))
    intervals = list(dict.fromkeys(interval.strip() for interval in settings.candle_intervals.split(",") if interval.strip()))
    return MarketConfigResponse(
        symbols=symbols,
        intervals=intervals,
        dashboard_refresh_seconds=15,
    )


@router.get("", response_model=list[CandleResponse], dependencies=[Depends(get_operator_session)])
def get_candles(
    symbol: str = Query(min_length=5, max_length=20),
    interval: str = Query(min_length=2, max_length=10),
    limit: int = Query(default=500, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    closed_only: bool = Query(default=True),
    service: CandleService = Depends(get_candle_service),
):
    return service.get_history(
        symbol,
        interval,
        limit=limit,
        offset=offset,
        closed_only=closed_only,
    )


@router.get("/latest", response_model=CandleResponse, dependencies=[Depends(get_operator_session)])
def get_latest_candle(
    symbol: str = Query(min_length=5, max_length=20),
    interval: str = Query(min_length=2, max_length=10),
    closed_only: bool = Query(default=False),
    service: CandleService = Depends(get_candle_service),
):
    candle = service.get_latest(
        symbol,
        interval,
        closed_only=closed_only,
    )
    if candle is None:
        raise HTTPException(status_code=404, detail="Candle não encontrado")
    return candle


@router.post("/sync", response_model=CandleSyncResponse, dependencies=[Depends(require_operator_csrf)])
async def sync_candles(
    payload: CandleSyncRequest,
    service: CandleService = Depends(get_candle_service),
):
    try:
        candles = await service.sync_incremental(
            payload.symbol,
            payload.interval,
            limit=payload.limit,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except (httpx.TimeoutException, httpx.HTTPError) as error:
        raise HTTPException(
            status_code=502,
            detail="Falha ao consultar dados de mercado na Binance",
        ) from error

    return CandleSyncResponse(
        symbol=payload.symbol,
        interval=payload.interval,
        synchronized=len(candles),
        candles=candles,
    )
