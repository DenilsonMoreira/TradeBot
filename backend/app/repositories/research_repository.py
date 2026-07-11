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
