from sqlalchemy import delete

from app.ai.registry import ModelRegistry
from app.database import SessionLocal
from app.models.research import DatasetArtifact, TrainedModel
from app.repositories.research_repository import ResearchRepository


def test_registry_keeps_one_active_model_per_dataset() -> None:
    with SessionLocal() as session:
        session.execute(delete(TrainedModel))
        session.execute(delete(DatasetArtifact))
        dataset = DatasetArtifact(
            symbol="BTCUSDT",
            interval="15m",
            version="registry-test-v1",
            feature_names=["return_1"],
            rows=[],
            train_size=1,
            test_size=1,
            metadata_json={"split": "temporal"},
        )
        session.add(dataset)
        session.flush()
        first = TrainedModel(
            dataset_id=dataset.id,
            algorithm="logistic_regression",
            version="model-v1",
            metrics={"strategy_return": 0.01},
            artifact_path="/tmp/first.joblib",
        )
        second = TrainedModel(
            dataset_id=dataset.id,
            algorithm="random_forest",
            version="model-v1",
            metrics={"strategy_return": 0.02},
            artifact_path="/tmp/second.joblib",
        )
        session.add_all([first, second])
        session.commit()

        registry = ModelRegistry(ResearchRepository(session))
        registry.promote(first.id)
        registry.promote(second.id)
        session.refresh(first)

        assert first.status == "INACTIVE"
        assert first.deactivated_at is not None
        assert second.status == "ACTIVE"
        assert registry.get_active(dataset.id).id == second.id
