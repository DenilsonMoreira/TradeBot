from dataclasses import asdict
from decimal import Decimal

from app.backtest.engine import BacktestConfig, run_ema_cross_backtest, serialize_trade
from app.models.research import BacktestRun
from app.repositories.candle_repository import CandleRepository
from app.repositories.research_repository import ResearchRepository


class BacktestService:
    def __init__(self, candles: CandleRepository, research: ResearchRepository):
        self.candles = candles
        self.research = research

    def run(self, symbol: str, interval: str, config: BacktestConfig, limit: int = 1000) -> BacktestRun:
        candles = list(reversed(self.candles.get_history(symbol, interval, limit=limit, closed_only=True)))
        result = run_ema_cross_backtest(candles, config)
        parameters = {key: str(value) for key, value in asdict(config).items()}
        run = BacktestRun(
            symbol=symbol.upper(), interval=interval, strategy="EMA_CROSS_V1",
            parameters=parameters, initial_capital=config.initial_capital,
            final_capital=result.final_capital, metrics=result.metrics,
            trades=[serialize_trade(trade) for trade in result.trades],
        )
        try:
            self.research.save(run)
            self.research.session.commit()
            self.research.session.refresh(run)
        except Exception:
            self.research.session.rollback()
            raise
        return run
