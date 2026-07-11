from decimal import Decimal

from app.ai.predictor import predict_probability
from app.models.prediction import Prediction
from app.repositories.research_repository import ResearchRepository


class PredictionService:
    def __init__(self, repository: ResearchRepository) -> None:
        self.repository = repository

    def predict(
        self,
        dataset_id: int,
        candle_id: int,
        features: dict[str, float],
    ) -> Prediction:
        dataset = self.repository.get_dataset(dataset_id)
        if dataset is None:
            raise ValueError("dataset não encontrado")
        model = self.repository.get_active_model(dataset_id)
        if model is None:
            raise ValueError("nenhum modelo ativo para o dataset")
        if set(features) != set(dataset.feature_names):
            raise ValueError("features não correspondem à versão do dataset")
        existing = self.repository.get_prediction(model.id, candle_id)
        if existing is not None:
            return existing

        member_paths = None
        if model.algorithm == "ensemble_soft_voting":
            member_ids = model.metrics.get("member_ids", [])
            members = self.repository.get_models_by_ids(member_ids)
            member_paths = {member.id: member.artifact_path for member in members}
        probability, threshold = predict_probability(
            model.algorithm,
            model.artifact_path,
            [features[name] for name in dataset.feature_names],
            member_paths,
        )
        prediction = Prediction(
            model_id=model.id,
            dataset_id=dataset_id,
            candle_id=candle_id,
            probability=Decimal(str(probability)),
            signal="BUY" if probability >= threshold else "HOLD",
            features=features,
        )
        try:
            self.repository.save(prediction)
            self.repository.session.commit()
            self.repository.session.refresh(prediction)
        except Exception:
            self.repository.session.rollback()
            raise
        return prediction
