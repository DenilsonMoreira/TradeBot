from datetime import UTC, datetime

from app.models.research import TrainedModel
from app.repositories.research_repository import ResearchRepository


class ModelRegistry:
    def __init__(self, repository: ResearchRepository) -> None:
        self.repository = repository

    def promote(self, model_id: int) -> TrainedModel:
        try:
            target = self.repository.get_model_for_update(model_id)
            if target is None:
                raise ValueError("modelo não encontrado")
            current = self.repository.get_active_model_for_update(
                target.dataset_id
            )
            now = datetime.now(UTC)
            if current is not None and current.id != target.id:
                current.status = "INACTIVE"
                current.deactivated_at = now
            target.status = "ACTIVE"
            target.promoted_at = target.promoted_at or now
            target.deactivated_at = None
            self.repository.session.commit()
            self.repository.session.refresh(target)
            return target
        except Exception:
            self.repository.session.rollback()
            raise

    def deactivate(self, model_id: int) -> TrainedModel:
        try:
            target = self.repository.get_model_for_update(model_id)
            if target is None:
                raise ValueError("modelo não encontrado")
            target.status = "INACTIVE"
            target.deactivated_at = datetime.now(UTC)
            self.repository.session.commit()
            self.repository.session.refresh(target)
            return target
        except Exception:
            self.repository.session.rollback()
            raise

    def get_active(self, dataset_id: int) -> TrainedModel | None:
        return self.repository.get_active_model(dataset_id)

    def recommend(
        self,
        dataset_id: int,
        *,
        min_strategy_return: float = 0.0,
        min_f1: float = 0.0,
        min_roc_auc: float = 0.0,
        min_trade_count: int = 0,
        require_outperform_buy_hold: bool = False,
    ) -> TrainedModel | None:
        candidates = []
        for model in self.repository.get_models_for_dataset(dataset_id):
            if model.algorithm == "baseline" or model.status == "INACTIVE":
                continue
            strategy_return = float(model.metrics.get("strategy_return", 0))
            f1 = float(model.metrics.get("f1", 0))
            roc_auc = float(model.metrics.get("roc_auc", 0))
            buy_and_hold = float(model.metrics.get("buy_and_hold_return", 0))
            trade_count = int(model.metrics.get("trade_count", 0))
            if (
                strategy_return >= min_strategy_return
                and f1 >= min_f1
                and roc_auc >= min_roc_auc
                and trade_count >= min_trade_count
                and (
                    not require_outperform_buy_hold
                    or strategy_return > buy_and_hold
                )
            ):
                candidates.append(
                    (strategy_return, f1, roc_auc, trade_count, model)
                )
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda item: (item[0], item[1], item[2], item[3]),
        )[4]
