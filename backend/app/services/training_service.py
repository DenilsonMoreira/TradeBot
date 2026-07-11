from app.ai.trainer import train_candidates
from app.models.research import TrainedModel
from app.repositories.research_repository import ResearchRepository

EXPECTED_ALGORITHMS = {
    "baseline",
    "logistic_regression",
    "random_forest",
    "xgboost",
    "lightgbm",
    "catboost",
}


class TrainingService:
    def __init__(self, research: ResearchRepository, artifact_dir: str):
        self.research = research
        self.artifact_dir = artifact_dir

    def train(self, dataset_id: int) -> list[TrainedModel]:
        dataset = self.research.get_dataset(dataset_id)
        if dataset is None:
            raise ValueError("dataset não encontrado")
        existing = list(self.research.get_models_for_dataset(dataset_id))
        existing_names = {model.algorithm for model in existing}
        missing = EXPECTED_ALGORITHMS - existing_names
        if not missing:
            return existing
        results = train_candidates(
            dataset.rows,
            dataset.feature_names,
            dataset.train_size,
            self.artifact_dir,
            dataset.version,
            algorithms=missing,
        )
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
        return sorted([*existing, *models], key=lambda model: model.algorithm)
