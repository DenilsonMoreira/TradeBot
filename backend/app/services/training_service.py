from app.ai.trainer import train_candidates
from app.models.research import TrainedModel
from app.repositories.research_repository import ResearchRepository


class TrainingService:
    def __init__(self, research: ResearchRepository, artifact_dir: str):
        self.research = research
        self.artifact_dir = artifact_dir

    def train(self, dataset_id: int) -> list[TrainedModel]:
        dataset = self.research.get_dataset(dataset_id)
        if dataset is None:
            raise ValueError("dataset não encontrado")
        existing = list(self.research.get_models_for_dataset(dataset_id))
        if existing:
            return existing
        results = train_candidates(dataset.rows, dataset.feature_names, dataset.train_size, self.artifact_dir, dataset.version)
        models = [TrainedModel(dataset_id=dataset.id, algorithm=name, version="model-v1", metrics=metrics, artifact_path=path) for name, metrics, path in results]
        try:
            for model in models:
                self.research.save(model)
            self.research.session.commit()
            for model in models:
                self.research.session.refresh(model)
        except Exception:
            self.research.session.rollback()
            raise
        return models
