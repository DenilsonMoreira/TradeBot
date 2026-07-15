from app.ai.datasets.builder import (
    FEATURE_NAMES,
    TARGET_RETURN_THRESHOLD,
    build_rows,
    dataset_version,
    validate_candle_continuity,
)
from app.models.research import DatasetArtifact
from app.repositories.candle_repository import CandleRepository
from app.repositories.research_repository import ResearchRepository


class DatasetService:
    def __init__(self, candles: CandleRepository, research: ResearchRepository):
        self.candles = candles
        self.research = research

    def build(self, symbol: str, interval: str, limit: int = 1000, horizon: int = 1, train_ratio: float = 0.8) -> DatasetArtifact:
        if not 0.5 <= train_ratio < 1:
            raise ValueError("train_ratio deve estar entre 0.5 e 1")
        candles = list(reversed(self.candles.get_history(symbol, interval, limit=limit, closed_only=True)))
        largest_gap = validate_candle_continuity(candles)
        rows = build_rows(candles, horizon)
        if len(rows) < 30:
            raise ValueError("dados insuficientes para criar dataset")
        train_size = int(len(rows) * train_ratio)
        version = dataset_version(symbol, interval, rows, horizon)
        existing = self.research.get_dataset_by_version(version)
        if existing is not None:
            return existing
        artifact = DatasetArtifact(
            symbol=symbol.upper(), interval=interval,
            version=version,
            feature_names=FEATURE_NAMES, rows=rows, train_size=train_size,
            test_size=len(rows) - train_size,
            metadata_json={"horizon": horizon, "train_ratio": train_ratio, "split": "temporal", "closed_candles_only": True, "max_candle_gap": largest_gap, "target_return_threshold": TARGET_RETURN_THRESHOLD, "evaluation_cost_rate_per_side": 0.0015},
        )
        try:
            self.research.save(artifact)
            self.research.session.commit()
            self.research.session.refresh(artifact)
        except Exception:
            self.research.session.rollback()
            raise
        return artifact
