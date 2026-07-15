import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ai.registry import ModelRegistry
from app.backtest.engine import BacktestConfig
from app.config import settings
from app.database import SessionLocal
from app.repositories.candle_repository import CandleRepository
from app.repositories.research_repository import ResearchRepository
from app.services.backtest_service import BacktestService
from app.services.dataset_service import DatasetService
from app.services.training_service import TrainingService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa backtest, cria dataset temporal e treina candidatos.",
    )
    parser.add_argument("--symbols", nargs="+", help="Ex.: BTCUSDT ETHUSDT")
    parser.add_argument("--interval", default="15m")
    parser.add_argument("--limit", type=int, default=3000)
    parser.add_argument("--horizon", type=int, default=1)
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--initial-capital", type=Decimal, default=Decimal("500"))
    parser.add_argument("--fee-rate", type=Decimal, default=Decimal("0.001"))
    parser.add_argument("--slippage-rate", type=Decimal, default=Decimal("0.0005"))
    parser.add_argument("--promote-qualified", action="store_true")
    parser.add_argument("--min-strategy-return", type=float, default=0.0)
    parser.add_argument("--min-f1", type=float, default=0.5)
    parser.add_argument("--min-roc-auc", type=float, default=0.55)
    parser.add_argument("--min-trades", type=int, default=20)
    parser.add_argument("--allow-underperform-buy-hold", action="store_true")
    parser.add_argument("--skip-backtest", action="store_true")
    parser.add_argument("--summary-only", action="store_true")
    return parser.parse_args()


def run_market(symbol: str, args: argparse.Namespace) -> dict:
    with SessionLocal() as session:
        candles = CandleRepository(session)
        research = ResearchRepository(session)
        backtest = None
        if not args.skip_backtest:
            backtest = BacktestService(candles, research).run(
                symbol,
                args.interval,
                BacktestConfig(
                    args.initial_capital,
                    args.fee_rate,
                    args.slippage_rate,
                ),
                args.limit,
            )
        dataset = DatasetService(candles, research).build(
            symbol,
            args.interval,
            args.limit,
            args.horizon,
            args.train_ratio,
        )
        models = TrainingService(
            research,
            settings.model_artifact_dir,
        ).train(dataset.id)
        registry = ModelRegistry(research)
        recommended = registry.recommend(
            dataset.id,
            min_strategy_return=args.min_strategy_return,
            min_f1=args.min_f1,
            min_roc_auc=args.min_roc_auc,
            min_trade_count=args.min_trades,
            require_outperform_buy_hold=not args.allow_underperform_buy_hold,
        )
        active = None
        if args.promote_qualified and recommended is not None:
            active = registry.promote(recommended.id)

        return {
            "symbol": symbol,
            "candles_requested": args.limit,
            "backtest": None if backtest is None else {
                "id": backtest.id,
                "final_capital": str(backtest.final_capital),
                "metrics": backtest.metrics,
            },
            "dataset": {
                "id": dataset.id,
                "version": dataset.version,
                "train_size": dataset.train_size,
                "test_size": dataset.test_size,
            },
            "models": [
                {
                    "id": model.id,
                    "algorithm": model.algorithm,
                    "status": model.status,
                    "metrics": (
                        {
                            key: model.metrics.get(key)
                            for key in (
                                "f1",
                                "roc_auc",
                                "strategy_return",
                                "buy_and_hold_return",
                                "trade_count",
                                "threshold",
                                "validation_strategy_return",
                                "validation_trade_count",
                            )
                        }
                        if args.summary_only
                        else model.metrics
                    ),
                }
                for model in models
            ],
            "recommended": recommended.algorithm if recommended else None,
            "activated": active.algorithm if active else None,
        }


def main() -> None:
    args = parse_args()
    if not 50 <= args.limit <= 10000:
        raise SystemExit("--limit deve estar entre 50 e 10000")
    configured = [
        item.strip().upper()
        for item in settings.candle_symbols.split(",")
        if item.strip()
    ]
    symbols = [item.upper() for item in (args.symbols or configured)]
    results = [run_market(symbol, args) for symbol in symbols]
    print(json.dumps(results, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
