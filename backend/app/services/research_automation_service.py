from datetime import datetime

from app.ai.registry import ModelRegistry
from app.repositories.candle_repository import CandleRepository
from app.repositories.research_repository import ResearchRepository
from app.services.dataset_service import DatasetService
from app.services.training_service import TrainingService


class ResearchAutomationService:
    def __init__(
        self,
        candles: CandleRepository,
        research: ResearchRepository,
        datasets: DatasetService,
        training: TrainingService,
        registry: ModelRegistry,
    ) -> None:
        self.candles = candles
        self.research = research
        self.datasets = datasets
        self.training = training
        self.registry = registry

    def evaluate_market(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int,
        horizon: int,
        train_ratio: float,
        minimum_new_candles: int = 0,
        promote_qualified: bool = False,
    ) -> dict:
        latest = self.research.get_latest_dataset(symbol, interval, horizon)
        if latest is None:
            available = self.candles.count(symbol, interval)
            required = max(limit, minimum_new_candles)
            last_evaluated_at = None
        else:
            last_evaluated_at = datetime.fromisoformat(
                latest.rows[-1]["open_time"]
            )
            available = self.candles.count_after(
                symbol,
                interval,
                last_evaluated_at,
            )
            # The horizon candles already existed after the last labelled row.
            # Adding them prevents overlap with the previous final test window.
            required = max(
                latest.test_size + horizon,
                minimum_new_candles,
            )

        result = {
            "symbol": symbol.upper(),
            "interval": interval,
            "due": available >= required,
            "available_new_candles": available,
            "required_new_candles": required,
            "last_evaluated_at": (
                last_evaluated_at.isoformat()
                if last_evaluated_at is not None
                else None
            ),
            "dataset_id": latest.id if latest is not None else None,
            "trained_models": 0,
            "recommended": None,
            "activated": None,
        }
        if not result["due"]:
            return result

        dataset = self.datasets.build(
            symbol,
            interval,
            limit,
            horizon,
            train_ratio,
        )
        if latest is not None and dataset.id == latest.id:
            result["due"] = False
            return result

        models = self.training.train(dataset.id)
        recommended = self.registry.recommend(
            dataset.id,
            min_strategy_return=0.0,
            min_f1=0.5,
            min_roc_auc=0.55,
            min_trade_count=20,
            min_walk_forward_return=0.0,
            min_profitable_folds=2,
            require_outperform_buy_hold=True,
        )
        activated = None
        if promote_qualified and recommended is not None:
            activated = self.registry.promote(recommended.id)

        result.update({
            "dataset_id": dataset.id,
            "trained_models": len(models),
            "recommended": recommended.algorithm if recommended else None,
            "activated": activated.algorithm if activated else None,
        })
        return result
