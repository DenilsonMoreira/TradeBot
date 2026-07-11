from decimal import Decimal
from math import sqrt

from app.backtest.simulator import BacktestTrade


def calculate_metrics(initial: Decimal, final: Decimal, trades: list[BacktestTrade], equity: list[Decimal]) -> dict:
    wins = [trade.pnl for trade in trades if trade.pnl > 0]
    losses = [trade.pnl for trade in trades if trade.pnl < 0]
    peak = equity[0] if equity else initial
    max_drawdown = Decimal(0)
    returns: list[float] = []
    for index, value in enumerate(equity):
        peak = max(peak, value)
        if peak:
            max_drawdown = max(max_drawdown, (peak - value) / peak * 100)
        if index and equity[index - 1]:
            returns.append(float(value / equity[index - 1] - 1))
    mean = sum(returns) / len(returns) if returns else 0.0
    variance = sum((item - mean) ** 2 for item in returns) / (len(returns) - 1) if len(returns) > 1 else 0.0
    sharpe = mean / sqrt(variance) * sqrt(365) if variance > 0 else 0.0
    gross_profit = sum(wins, Decimal(0))
    gross_loss = abs(sum(losses, Decimal(0)))
    return {
        "net_profit": str(final - initial),
        "return_percent": str((final / initial - 1) * 100 if initial else 0),
        "max_drawdown_percent": str(max_drawdown),
        "win_rate_percent": str(Decimal(len(wins)) / Decimal(len(trades)) * 100 if trades else 0),
        "profit_factor": str(gross_profit / gross_loss) if gross_loss else None,
        "expectancy": str((final - initial) / len(trades)) if trades else "0",
        "sharpe_ratio": sharpe,
        "trade_count": len(trades),
        "average_win": str(gross_profit / len(wins)) if wins else "0",
        "average_loss": str(gross_loss / len(losses)) if losses else "0",
    }
