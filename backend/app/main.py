from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.binance_client import BinanceTestnetClient
from app.config import settings
from app.database import Base, engine, get_db
from app.models import BotMode, BotStatus, Order, Position, Signal
from app.trading_service import execute_market_buy, execute_market_sell
from app.schemas import (
    BotModeUpdate,
    BotStatusResponse,
    SignalCreate,
    SignalResponse,    
    ManualBuyRequest,
    ManualSellRequest,
    OrderResponse,
    PositionResponse,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        status = db.get(BotStatus, 1)
        if status is None:
            db.add(BotStatus(id=1, mode=BotMode.OFF))
            db.commit()

    yield


app = FastAPI(
    title="TradeBot API",
    version="0.2.0",
    description="Bot de trading em modo Binance Spot Testnet",
    lifespan=lifespan,
)

binance = BinanceTestnetClient()

RELEVANT_ASSETS = {"USDT", "BTC", "ETH", "BNB", "SOL", "XRP"}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "environment": "testnet" if settings.binance_testnet else "live",
    }


@app.get("/market/{symbol}/candles")
async def market_candles(
    symbol: str,
    interval: str = Query(default="15m"),
    limit: int = Query(default=100, ge=1, le=1000),
):
    try:
        candles = await binance.get_candles(symbol, interval, limit)
        return {
            "symbol": symbol.upper(),
            "interval": interval,
            "count": len(candles),
            "candles": candles,
        }
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error))


@app.get("/account/balance")
async def account_balance():
    try:
        account = await binance.get_account()

        balances = [
            {
                "asset": item["asset"],
                "free": item["free"],
                "locked": item["locked"],
            }
            for item in account["balances"]
            if item["asset"] in RELEVANT_ASSETS
            and (float(item["free"]) > 0 or float(item["locked"]) > 0)
        ]

        return {
            "environment": "testnet" if settings.binance_testnet else "live",
            "balances": balances,
        }
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Não foi possível consultar a conta Testnet. Detalhe: {error}",
        )


@app.get("/bot/status", response_model=BotStatusResponse)
def get_bot_status(db: Session = Depends(get_db)):
    status = db.get(BotStatus, 1)
    if status is None:
        raise HTTPException(status_code=500, detail="Status do bot não inicializado")
    return status


@app.put("/bot/status", response_model=BotStatusResponse)
def update_bot_status(
    payload: BotModeUpdate,
    db: Session = Depends(get_db),
):
    if payload.mode == BotMode.TESTNET_TRADING:
        if payload.confirmation != "ATIVAR TESTNET":
            raise HTTPException(
                status_code=400,
                detail=(
                    "Para ativar TESTNET_TRADING, envie "
                    '`"confirmation": "ATIVAR TESTNET"`'
                ),
            )

    status = db.get(BotStatus, 1)
    if status is None:
        status = BotStatus(id=1, mode=payload.mode)
        db.add(status)
    else:
        status.mode = payload.mode

    db.commit()
    db.refresh(status)
    return status


@app.post("/signals", response_model=SignalResponse, status_code=201)
def create_signal(
    payload: SignalCreate,
    db: Session = Depends(get_db),
):
    signal = Signal(
        symbol=payload.symbol.upper(),
        timeframe=payload.timeframe,
        signal_type=payload.signal_type.upper(),
        price=payload.price,
        confidence=payload.confidence,
        strategy_name=payload.strategy_name,
        details=payload.details,
    )

    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


@app.get("/signals", response_model=list[SignalResponse])
def list_signals(
    symbol: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = select(Signal).order_by(Signal.created_at.desc()).limit(limit)

    if symbol:
        query = (
            select(Signal)
            .where(Signal.symbol == symbol.upper())
            .order_by(Signal.created_at.desc())
            .limit(limit)
        )

    return list(db.scalars(query).all())

@app.post(
    "/trading/manual-buy",
    response_model=OrderResponse,
    status_code=201,
)
async def manual_buy(
    payload: ManualBuyRequest,
    db: Session = Depends(get_db),
):
    status = db.get(BotStatus, 1)

    if status is None or status.mode != BotMode.TESTNET_TRADING:
        raise HTTPException(
            status_code=400,
            detail="O bot precisa estar em TESTNET_TRADING para comprar.",
        )

    if payload.confirmation != "COMPRAR BTC TESTNET":
        raise HTTPException(
            status_code=400,
            detail=(
                "Confirmação inválida. Envie "
                '`"confirmation": "COMPRAR BTC TESTNET"`'
            ),
        )

    try:
        return await execute_market_buy(
            db=db,
            client=binance,
            quote_amount=payload.quote_amount,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Falha ao enviar ordem para Binance Testnet: {error}",
        )


@app.get("/orders", response_model=list[OrderResponse])
def list_orders(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    statement = (
        select(Order)
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement).all())

@app.post(
    "/trading/manual-sell",
    response_model=OrderResponse,
    status_code=201,
)
async def manual_sell(
    payload: ManualSellRequest,
    db: Session = Depends(get_db),
):
    status = db.get(BotStatus, 1)

    if status is None or status.mode != BotMode.TESTNET_TRADING:
        raise HTTPException(
            status_code=400,
            detail="O bot precisa estar em TESTNET_TRADING para vender.",
        )

    if payload.confirmation != "VENDER BTC TESTNET":
        raise HTTPException(
            status_code=400,
            detail=(
                "Confirmação inválida. Envie "
                '`"confirmation": "VENDER BTC TESTNET"`'
            ),
        )

    try:
        return await execute_market_sell(db=db, client=binance)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Falha ao vender na Binance Testnet: {error}",
        )


@app.get("/positions", response_model=list[PositionResponse])
def list_positions(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    statement = select(Position).order_by(Position.opened_at.desc()).limit(limit)

    if status:
        statement = (
            select(Position)
            .where(Position.status == status.upper())
            .order_by(Position.opened_at.desc())
            .limit(limit)
        )

    return list(db.scalars(statement).all())