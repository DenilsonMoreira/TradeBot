from app.ai.artifact_validation import validate_model_artifact
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
MODEL_VERSION = "model-v4-walk-forward-purged"


class TrainingService:
    def __init__(self, research: ResearchRepository, artifact_dir: str):
        self.research = research
        self.artifact_dir = artifact_dir

    def train(self, dataset_id: int) -> list[TrainedModel]:
        dataset = self.research.get_dataset(dataset_id)
        if dataset is None:
            raise ValueError("dataset não encontrado")
        existing = [
            model
            for model in self.research.get_models_for_dataset(dataset_id)
            if model.version == MODEL_VERSION
        ]
        existing_by_name = {model.algorithm: model for model in existing}
        missing = {
            name for name in EXPECTED_ALGORITHMS
            if name not in existing_by_name or not validate_model_artifact(existing_by_name[name].artifact_path)[0]
        }
        if not missing:
            return existing
        results = train_candidates(
            dataset.rows,
            dataset.feature_names,
            dataset.train_size,
            self.artifact_dir,
            f"{dataset.version}-{MODEL_VERSION}",
            algorithms=missing,
            holding_period=int(dataset.metadata_json.get("horizon", 1)),
            cost_rate=float(
                dataset.metadata_json.get(
                    "evaluation_cost_rate_per_side",
                    0.0015,
                )
            ),
        )
        models = []
        for name, metrics, path in results:
            model = existing_by_name.get(name)
            if model is None:
                model = TrainedModel(dataset_id=dataset.id, algorithm=name, version=MODEL_VERSION, metrics=metrics, artifact_path=path)
            else:
                model.metrics = metrics
                model.artifact_path = path
            models.append(model)
        try:
            for model in models:
                self.research.save(model)
            self.research.session.commit()
            for model in models:
                self.research.session.refresh(model)
        except Exception:
            self.research.session.rollback()
            raise
        final = {model.algorithm: model for model in [*existing, *models]}
        return sorted(final.values(), key=lambda model: model.algorithm)
