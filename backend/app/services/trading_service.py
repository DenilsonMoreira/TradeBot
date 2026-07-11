import json
import logging

from sqlalchemy import select, func
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.binance_client import BinanceTestnetClient
from app.models import (
    Order,
    OrderStatus,
    Position,
    PositionStatus,
    TradingRiskSettings
)

logger = logging.getLogger(__name__)

TRADE_SYMBOL = "BTCUSDT"
FIXED_QUOTE_AMOUNT = 20.0


def has_open_position(db: Session, symbol: str) -> bool:
    statement = (
        select(Position.id)
        .where(
            Position.symbol == symbol,
            Position.status == PositionStatus.OPEN,
        )
        .limit(1)
    )
    return db.scalar(statement) is not None


async def execute_market_buy(
    db: Session,
    client: BinanceTestnetClient,
    symbol: str = TRADE_SYMBOL,
    quote_amount: float = FIXED_QUOTE_AMOUNT,
) -> Order:
    symbol = symbol.upper()

    if symbol != TRADE_SYMBOL:
        raise ValueError(f"Somente {TRADE_SYMBOL} está permitido nesta fase.")

    if has_open_position(db, symbol):
        raise ValueError(f"Já existe uma posição aberta para {symbol}.")

    order = Order(
        symbol=symbol,
        side="BUY",
        order_type="MARKET",
        status=OrderStatus.PENDING,
        requested_quote_amount=quote_amount,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    try:
        response = await client.create_market_buy_order(
            symbol=symbol,
            quote_order_qty=quote_amount,
        )

        fills = response.get("fills", [])
        executed_quantity = float(response.get("executedQty", 0))

        if executed_quantity <= 0:
            raise ValueError("A Binance retornou quantidade executada inválida.")

        total_quote = sum(
            float(fill["price"]) * float(fill["qty"])
            for fill in fills
        )

        executed_price = (
            total_quote / executed_quantity
            if total_quote > 0
            else float(response.get("cummulativeQuoteQty", 0))
            / executed_quantity
        )

        order.status = OrderStatus.FILLED
        order.exchange_order_id = str(response["orderId"])
        order.executed_quantity = executed_quantity
        order.executed_price = executed_price
        order.raw_response = json.dumps(response)
        db.commit()
        db.refresh(order)

        executed_quote_amount = float(
            response.get("cummulativeQuoteQty", 0)
        )

        if executed_quote_amount <= 0:
            executed_quote_amount = executed_quantity * executed_price

        position = Position(
            symbol=symbol,
            status=PositionStatus.OPEN,
            entry_order_id=order.id,
            quantity=executed_quantity,
            entry_price=executed_price,
            invested_quote_amount=executed_quote_amount,
            stop_loss=executed_price * 0.98,
            take_profit=executed_price * 1.04,
        )
        db.add(position)
        db.commit()

        logger.info(
            "Compra executada: %s | quantidade=%s | preço=%s",
            symbol,
            executed_quantity,
            executed_price,
        )

        return order

    except Exception as error:
        order.status = OrderStatus.REJECTED
        order.error_message = str(error)
        db.commit()
        raise

async def execute_market_sell(
    db: Session,
    client: BinanceTestnetClient,
    symbol: str = TRADE_SYMBOL,
    close_reason: str = "MANUAL",
) -> Order:
    symbol = symbol.upper()

    position = db.scalar(
        select(Position)
        .where(
            Position.symbol == symbol,
            Position.status == PositionStatus.OPEN,
        )
        .order_by(Position.opened_at.desc())
        .limit(1)
    )

    if position is None:
        raise ValueError(f"Não existe posição aberta para {symbol}.")

    order = Order(
        symbol=symbol,
        side="SELL",
        order_type="MARKET",
        status=OrderStatus.PENDING,
        requested_quote_amount=position.invested_quote_amount,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    try:
        response = await client.create_market_sell_order(
            symbol=symbol,
            quantity=position.quantity,
        )

        fills = response.get("fills", [])
        executed_quantity = float(response.get("executedQty", 0))

        if executed_quantity <= 0:
            raise ValueError("A Binance retornou quantidade vendida inválida.")

        received_quote_amount = sum(
            float(fill["price"]) * float(fill["qty"])
            for fill in fills
        )

        if received_quote_amount <= 0:
            received_quote_amount = float(
                response.get("cummulativeQuoteQty", 0)
            )

        exit_price = received_quote_amount / executed_quantity

        order.status = OrderStatus.FILLED
        order.exchange_order_id = str(response["orderId"])
        order.executed_quantity = executed_quantity
        order.executed_price = exit_price
        order.raw_response = json.dumps(response)
        db.commit()
        db.refresh(order)

        realized_pnl = (
            received_quote_amount - position.invested_quote_amount
        )
        realized_pnl_percent = (
            realized_pnl / position.invested_quote_amount
        ) * 100

        position.status = PositionStatus.CLOSED
        position.exit_order_id = order.id
        position.exit_price = exit_price
        position.received_quote_amount = received_quote_amount
        position.realized_pnl = realized_pnl
        position.realized_pnl_percent = realized_pnl_percent
        position.close_reason = close_reason
        position.closed_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(
            "Venda executada: %s | P&L=%s USDT (%s%%)",
            symbol,
            realized_pnl,
            realized_pnl_percent,
        )

        return order

    except Exception as error:
        order.status = OrderStatus.REJECTED
        order.error_message = str(error)
        db.commit()
        raise

def can_open_automatic_position(
    db: Session,
    symbol: str,
) -> tuple[bool, str]:
    settings = db.get(TradingRiskSettings, 1)

    if settings is None:
        return False, "Configurações de risco não encontradas."

    if not settings.auto_entry_enabled:
        return False, "Entrada automática está desativada."

    open_positions = db.scalar(
        select(func.count(Position.id)).where(
            Position.status == PositionStatus.OPEN
        )
    )

    if open_positions >= settings.max_open_positions:
        return False, "Limite de posições abertas atingido."

    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    daily_pnl = db.scalar(
        select(func.coalesce(func.sum(Position.realized_pnl), 0.0)).where(
            Position.status == PositionStatus.CLOSED,
            Position.closed_at >= day_start,
        )
    )

    if daily_pnl <= -settings.max_daily_loss:
        return False, "Limite de perda diária atingido."

    last_position = db.scalar(
        select(Position)
        .where(Position.symbol == symbol)
        .order_by(Position.opened_at.desc())
        .limit(1)
    )

    if last_position is not None:
        cooldown_until = last_position.opened_at + timedelta(
            minutes=settings.cooldown_minutes
        )

        if now < cooldown_until:
            return False, (
                f"Cooldown ativo até {cooldown_until.isoformat()}."
            )

    return True, "Entrada automática permitida."