from dataclasses import asdict, dataclass
from decimal import Decimal

from app.backtest.metrics import calculate_metrics
from app.backtest.simulator import BacktestTrade, apply_buy, apply_sell
from app.indicators.ema import calculate_ema
from app.models.candle import Candle


@dataclass(frozen=True)
class BacktestConfig:
    initial_capital: Decimal = Decimal("1000")
    fee_rate: Decimal = Decimal("0.001")
    slippage_rate: Decimal = Decimal("0.0005")
    fast_period: int = 9
    slow_period: int = 21


@dataclass(frozen=True)
class BacktestResult:
    final_capital: Decimal
    metrics: dict
    trades: list[BacktestTrade]


def run_ema_cross_backtest(candles: list[Candle], config: BacktestConfig) -> BacktestResult:
    if len(candles) < config.slow_period + 2:
        raise ValueError("candles insuficientes para o backtest")
    if config.fast_period >= config.slow_period:
        raise ValueError("fast_period deve ser menor que slow_period")
    if any(not candle.is_closed for candle in candles):
        raise ValueError("backtest aceita somente candles fechados")
    closes = [candle.close for candle in candles]
    fast = calculate_ema(closes, config.fast_period)
    slow = calculate_ema(closes, config.slow_period)
    capital = config.initial_capital
    quantity = Decimal(0)
    entry_price = Decimal(0)
    entry_time = candles[0].open_time
    entry_cost = Decimal(0)
    trades: list[BacktestTrade] = []
    equity = [capital]
    for index in range(1, len(candles) - 1):
        bullish = fast[index - 1] <= slow[index - 1] and fast[index] > slow[index]
        bearish = fast[index - 1] >= slow[index - 1] and fast[index] < slow[index]
        execution = candles[index + 1]
        if bullish and quantity == 0:
            entry_price, quantity = apply_buy(execution.open, capital, config.fee_rate, config.slippage_rate)
            entry_cost = capital
            entry_time = execution.open_time
            capital = Decimal(0)
        elif bearish and quantity > 0:
            exit_price, proceeds = apply_sell(execution.open, quantity, config.fee_rate, config.slippage_rate)
            pnl = proceeds - entry_cost
            trades.append(BacktestTrade(entry_time, execution.open_time, entry_price, exit_price, quantity, pnl, pnl / entry_cost * 100))
            capital, quantity = proceeds, Decimal(0)
        equity.append(capital if quantity == 0 else quantity * candles[index].close)
    if quantity > 0:
        exit_price, proceeds = apply_sell(candles[-1].close, quantity, config.fee_rate, config.slippage_rate)
        pnl = proceeds - entry_cost
        trades.append(BacktestTrade(entry_time, candles[-1].close_time, entry_price, exit_price, quantity, pnl, pnl / entry_cost * 100))
        capital = proceeds
    equity.append(capital)
    return BacktestResult(capital, calculate_metrics(config.initial_capital, capital, trades, equity), trades)


def serialize_trade(trade: BacktestTrade) -> dict:
    values = asdict(trade)
    return {key: value.isoformat() if hasattr(value, "isoformat") else str(value) for key, value in values.items()}
