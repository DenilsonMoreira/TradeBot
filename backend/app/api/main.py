from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.binance.client import BinanceTestnetClient
from app.config import settings
from app.database import Base, SessionLocal, engine, get_db
from app.models import (
    BotMode,
    BotStatus,
    Order,
    Position,
    Signal,
    TradingRiskSettings,
)
from app.schemas import (
    BotModeUpdate,
    BotStatusResponse,
    ManualBuyRequest,
    ManualSellRequest,
    OrderResponse,
    PositionResponse,
    SignalCreate,
    SignalResponse,
    TradingRiskSettingsResponse,
    TradingRiskSettingsUpdate,
)
from app.services.trading_service import execute_market_buy, execute_market_sell
from app.api.routes.candles import router as candles_router
from app.api.routes.indicators import router as indicators_router
from app.api.routes.research import router as research_router
from app.api.routes.auth import router as auth_router
from app.api.dependencies import get_audit_service, get_notification_service, get_operator_session, require_operator_csrf
from app.api.routes.audit import router as audit_router
from app.core.security import OperatorSession
from app.services.audit_service import AuditService
from app.api.routes.notifications import router as notifications_router
from app.services.notification_service import NotificationService


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Compatibilidade temporária para as tabelas legadas (fases 1–7).
    # Novas alterações de schema, como candles, são aplicadas por Alembic.
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        status = db.get(BotStatus, 1)
        if status is None:
            db.add(BotStatus(id=1, mode=BotMode.OFF))

        risk_settings = db.get(TradingRiskSettings, 1)
        if risk_settings is None:
            db.add(
                TradingRiskSettings(
                    id=1,
                    auto_entry_enabled=False,
                    max_quote_amount_per_trade=6.0,
                    max_daily_loss=40.0,
                    max_open_positions=1,
                    cooldown_minutes=30,
                )
            )

        db.commit()

    yield


app = FastAPI(
    title="TradeBot API",
    version="0.7.0",
    description="Bot de trading em modo Binance Spot Testnet",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.cors_origins.split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(candles_router)
app.include_router(indicators_router)
app.include_router(research_router)
app.include_router(auth_router)
app.include_router(audit_router)
app.include_router(notifications_router)

binance = BinanceTestnetClient()

RELEVANT_ASSETS = {"USDT", "BTC", "ETH", "BNB", "SOL", "XRP"}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "environment": "testnet" if settings.binance_testnet else "live",
    }


@app.get("/health/ready")
def readiness(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {
        "status": "ready",
        "database": "ok",
        "environment": "testnet" if settings.binance_testnet else "live",
    }


@app.get("/market/{symbol}/candles", dependencies=[Depends(get_operator_session)])
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


@app.get("/account/balance", dependencies=[Depends(get_operator_session)])
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


@app.get("/bot/status", response_model=BotStatusResponse, dependencies=[Depends(get_operator_session)])
def get_bot_status(db: Session = Depends(get_db)):
    status = db.get(BotStatus, 1)

    if status is None:
        raise HTTPException(
            status_code=500,
            detail="Status do bot não inicializado.",
        )

    return status


@app.put("/bot/status", response_model=BotStatusResponse)
def update_bot_status(
    payload: BotModeUpdate,
    db: Session = Depends(get_db),
    session: OperatorSession = Depends(require_operator_csrf),
    audit: AuditService = Depends(get_audit_service),
    notifications: NotificationService = Depends(get_notification_service),
):
    if (
        payload.mode == BotMode.TESTNET_TRADING
        and payload.confirmation != "ATIVAR TESTNET"
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Para ativar TESTNET_TRADING, envie "
                '"confirmation": "ATIVAR TESTNET".'
            ),
        )

    status = db.get(BotStatus, 1)

    if status is None:
        status = BotStatus(id=1, mode=payload.mode)
        db.add(status)
    else:
        status.mode = payload.mode

    db.flush()
    audit.record(session.email, "BOT_MODE_CHANGED", "bot", resource_id="1", details={"mode": payload.mode.value})
    notifications.create(session.email, "INFO", "BOT_MODE_CHANGED", "Modo operacional alterado", f"O bot foi alterado para {payload.mode.value}.", resource_id="1")
    db.refresh(status)
    return status


@app.post("/bot/emergency-stop", response_model=BotStatusResponse)
def emergency_stop(db: Session = Depends(get_db), session: OperatorSession = Depends(require_operator_csrf), audit: AuditService = Depends(get_audit_service), notifications: NotificationService = Depends(get_notification_service)):
    status = db.get(BotStatus, 1)

    if status is None:
        status = BotStatus(id=1, mode=BotMode.OFF)
        db.add(status)
    else:
        status.mode = BotMode.OFF

    db.flush()
    audit.record(session.email, "EMERGENCY_STOP", "bot", resource_id="1", details={"mode": "OFF"})
    notifications.create(session.email, "CRITICAL", "EMERGENCY_STOP", "Parada de emergência acionada", "O bot foi desligado e novas entradas foram bloqueadas.", resource_id="1")
    db.refresh(status)
    return status


@app.post("/signals", response_model=SignalResponse, status_code=201, dependencies=[Depends(require_operator_csrf)])
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


@app.get("/signals", response_model=list[SignalResponse], dependencies=[Depends(get_operator_session)])
def list_signals(
    symbol: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    statement = select(Signal).order_by(Signal.created_at.desc()).limit(limit)

    if symbol:
        statement = (
            select(Signal)
            .where(Signal.symbol == symbol.upper())
            .order_by(Signal.created_at.desc())
            .limit(limit)
        )

    return list(db.scalars(statement).all())


@app.post(
    "/trading/manual-buy",
    response_model=OrderResponse,
    status_code=201,
)
async def manual_buy(
    payload: ManualBuyRequest,
    db: Session = Depends(get_db),
    session: OperatorSession = Depends(require_operator_csrf),
    audit: AuditService = Depends(get_audit_service),
    notifications: NotificationService = Depends(get_notification_service),
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
                '"confirmation": "COMPRAR BTC TESTNET".'
            ),
        )

    try:
        order = await execute_market_buy(
            db=db,
            client=binance,
            quote_amount=payload.quote_amount,
        )
        audit.record(session.email, "MANUAL_BUY", "order", resource_id=str(order.id), details={"symbol": order.symbol, "quote_amount": payload.quote_amount, "environment": "testnet"})
        notifications.create(session.email, "INFO", "MANUAL_BUY", "Compra Testnet executada", f"Compra manual de {order.symbol} solicitada com US$ {payload.quote_amount:.2f}.", resource_id=str(order.id))
        return order
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Falha ao enviar ordem para Binance Testnet: {error}",
        )


@app.post(
    "/trading/manual-sell",
    response_model=OrderResponse,
    status_code=201,
)
async def manual_sell(
    payload: ManualSellRequest,
    db: Session = Depends(get_db),
    session: OperatorSession = Depends(require_operator_csrf),
    audit: AuditService = Depends(get_audit_service),
    notifications: NotificationService = Depends(get_notification_service),
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
                '"confirmation": "VENDER BTC TESTNET".'
            ),
        )

    try:
        order = await execute_market_sell(
            db=db,
            client=binance,
            close_reason="MANUAL",
        )
        audit.record(session.email, "MANUAL_SELL", "order", resource_id=str(order.id), details={"symbol": order.symbol, "environment": "testnet"})
        notifications.create(session.email, "INFO", "MANUAL_SELL", "Venda Testnet executada", f"Venda manual de {order.symbol} registrada.", resource_id=str(order.id))
        return order
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Falha ao vender na Binance Testnet: {error}",
        )


@app.get("/orders", response_model=list[OrderResponse], dependencies=[Depends(get_operator_session)])
def list_orders(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    statement = select(Order).order_by(Order.created_at.desc()).limit(limit)
    return list(db.scalars(statement).all())


@app.get("/positions", response_model=list[PositionResponse], dependencies=[Depends(get_operator_session)])
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


@app.get(
    "/trading/risk-settings",
    response_model=TradingRiskSettingsResponse,
    dependencies=[Depends(get_operator_session)],
)
def get_risk_settings(db: Session = Depends(get_db)):
    risk_settings = db.get(TradingRiskSettings, 1)

    if risk_settings is None:
        raise HTTPException(
            status_code=500,
            detail="Configurações de risco não inicializadas.",
        )

    return risk_settings


@app.put(
    "/trading/risk-settings",
    response_model=TradingRiskSettingsResponse,
)
def update_risk_settings(
    payload: TradingRiskSettingsUpdate,
    db: Session = Depends(get_db),
    session: OperatorSession = Depends(require_operator_csrf),
    audit: AuditService = Depends(get_audit_service),
    notifications: NotificationService = Depends(get_notification_service),
):
    if (
        payload.auto_entry_enabled
        and payload.confirmation != "ATIVAR ENTRADA AUTOMATICA"
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Para ativar entrada automática, envie "
                '"confirmation": "ATIVAR ENTRADA AUTOMATICA".'
            ),
        )

    risk_settings = db.get(TradingRiskSettings, 1)

    if risk_settings is None:
        risk_settings = TradingRiskSettings(id=1)
        db.add(risk_settings)

    risk_settings.auto_entry_enabled = payload.auto_entry_enabled
    risk_settings.max_quote_amount_per_trade = (
        payload.max_quote_amount_per_trade
    )
    risk_settings.max_daily_loss = payload.max_daily_loss
    risk_settings.max_open_positions = payload.max_open_positions
    risk_settings.cooldown_minutes = payload.cooldown_minutes

    db.flush()
    audit.record(session.email, "RISK_SETTINGS_CHANGED", "risk_settings", resource_id="1", details={"auto_entry_enabled": payload.auto_entry_enabled, "max_quote_amount_per_trade": payload.max_quote_amount_per_trade, "max_daily_loss": payload.max_daily_loss, "max_open_positions": payload.max_open_positions, "cooldown_minutes": payload.cooldown_minutes})
    notifications.create(session.email, "WARNING", "RISK_SETTINGS_CHANGED", "Limites de risco atualizados", f"Perda diária máxima: US$ {payload.max_daily_loss:.2f}; cooldown: {payload.cooldown_minutes} minutos.", resource_id="1")
    db.refresh(risk_settings)
    return risk_settings
