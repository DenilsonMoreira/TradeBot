from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class BacktestTrade:
    entry_time: datetime
    exit_time: datetime
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal
    pnl: Decimal
    return_percent: Decimal


def apply_buy(price: Decimal, capital: Decimal, fee: Decimal, slippage: Decimal) -> tuple[Decimal, Decimal]:
    executed = price * (Decimal(1) + slippage)
    quantity = capital / (executed * (Decimal(1) + fee))
    return executed, quantity


def apply_sell(price: Decimal, quantity: Decimal, fee: Decimal, slippage: Decimal) -> tuple[Decimal, Decimal]:
    executed = price * (Decimal(1) - slippage)
    proceeds = quantity * executed * (Decimal(1) - fee)
    return executed, proceeds
