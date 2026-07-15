from datetime import UTC, datetime, timedelta

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

    def get_market_status(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int,
        horizon: int,
        minimum_new_candles: int = 0,
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
            required = max(
                latest.test_size + horizon,
                minimum_new_candles,
            )

        missing = max(0, required - available)
        estimated_ready_at = None
        interval_seconds = _interval_seconds(interval)
        if missing and interval_seconds is not None:
            estimated_ready_at = (
                datetime.now(UTC) + timedelta(seconds=missing * interval_seconds)
            ).isoformat()
        return {
            "symbol": symbol.upper(),
            "interval": interval,
            "due": available >= required,
            "available_new_candles": available,
            "required_new_candles": required,
            "missing_candles": missing,
            "progress_percent": min(100.0, available / max(required, 1) * 100),
            "last_evaluated_at": (
                last_evaluated_at.isoformat()
                if last_evaluated_at is not None
                else None
            ),
            "estimated_ready_at": estimated_ready_at,
            "dataset_id": latest.id if latest is not None else None,
        }

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
        result = {
            **self.get_market_status(
                symbol,
                interval,
                limit=limit,
                horizon=horizon,
                minimum_new_candles=minimum_new_candles,
            ),
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


def _interval_seconds(interval: str) -> int | None:
    units = {"m": 60, "h": 3600, "d": 86400}
    if len(interval) < 2 or interval[-1] not in units:
        return None
    try:
        return int(interval[:-1]) * units[interval[-1]]
    except ValueError:
        return None
