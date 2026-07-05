import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.binance_client import BinanceTestnetClient
from app.models import (
    Order,
    OrderStatus,
    Position,
    PositionStatus,
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

        position = Position(
            symbol=symbol,
            status=PositionStatus.OPEN,
            entry_order_id=order.id,
            quantity=executed_quantity,
            entry_price=executed_price,
            invested_quote_amount=quote_amount,
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