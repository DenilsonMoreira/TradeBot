from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.research import BacktestRun, DatasetArtifact, TrainedModel


class ResearchRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save(self, item):
        self.session.add(item)
        self.session.flush()
        return item

    def list_backtests(self, limit: int = 50):
        return self.session.scalars(select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(limit)).all()

    def list_datasets(self, limit: int = 50):
        return self.session.scalars(select(DatasetArtifact).order_by(DatasetArtifact.created_at.desc()).limit(limit)).all()

    def get_dataset(self, dataset_id: int):
        return self.session.get(DatasetArtifact, dataset_id)

    def get_dataset_by_version(self, version: str):
        return self.session.scalar(
            select(DatasetArtifact).where(DatasetArtifact.version == version)
        )

    def list_models(self, limit: int = 50):
        return self.session.scalars(select(TrainedModel).order_by(TrainedModel.created_at.desc()).limit(limit)).all()

    def get_models_for_dataset(self, dataset_id: int):
        return self.session.scalars(
            select(TrainedModel)
            .where(TrainedModel.dataset_id == dataset_id)
            .order_by(TrainedModel.algorithm)
        ).all()

    def get_models_by_ids(self, model_ids: list[int]):
        if not model_ids:
            return []
        return self.session.scalars(
            select(TrainedModel)
            .where(TrainedModel.id.in_(model_ids))
            .order_by(TrainedModel.id)
        ).all()

    def get_model_by_identity(
        self,
        dataset_id: int,
        algorithm: str,
        version: str,
    ):
        return self.session.scalar(
            select(TrainedModel).where(
                TrainedModel.dataset_id == dataset_id,
                TrainedModel.algorithm == algorithm,
                TrainedModel.version == version,
            )
        )

    def get_model_for_update(self, model_id: int):
        return self.session.scalar(
            select(TrainedModel)
            .where(TrainedModel.id == model_id)
            .with_for_update()
        )

    def get_active_model(self, dataset_id: int):
        return self.session.scalar(
            select(TrainedModel).where(
                TrainedModel.dataset_id == dataset_id,
                TrainedModel.status == "ACTIVE",
            )
        )

    def get_active_model_for_update(self, dataset_id: int):
        return self.session.scalar(
            select(TrainedModel)
            .where(
                TrainedModel.dataset_id == dataset_id,
                TrainedModel.status == "ACTIVE",
            )
            .with_for_update()
        )
