from pathlib import Path
from types import SimpleNamespace

import joblib
from sklearn.dummy import DummyClassifier

from app.services.artifact_recovery_service import ArtifactRecoveryService, RECOVERY_PIPELINE


class FakeSession:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class FakeRepository:
    def __init__(self, dataset, models):
        self.dataset = dataset
        self.models = models
        self.session = FakeSession()

    def list_all_datasets(self):
        return [self.dataset]

    def list_all_models(self):
        return self.models

    def get_models_for_dataset(self, dataset_id):
        return [model for model in self.models if model.dataset_id == dataset_id]


def test_recovery_trains_algorithm_once_and_restores_all_versions(tmp_path):
    dataset = SimpleNamespace(
        id=1,
        symbol="BTCUSDT",
        version="dataset-test",
        rows=[{"features": {"a": 0.0}, "label": 0, "future_return": 0.0}],
        feature_names=["a"],
        train_size=80,
        metadata_json={"horizon": 1},
    )
    models = [
        SimpleNamespace(id=1, dataset_id=1, algorithm="baseline", version="model-v1", metrics={}, artifact_path="/old/one.joblib", status="CANDIDATE"),
        SimpleNamespace(id=2, dataset_id=1, algorithm="baseline", version="model-v2", metrics={}, artifact_path="/old/two.joblib", status="INACTIVE"),
    ]
    calls = []

    def fake_trainer(rows, feature_names, train_size, artifact_dir, version, algorithms, **kwargs):
        calls.append(algorithms)
        model = DummyClassifier(strategy="most_frequent").fit([[0.0], [1.0]], [0, 1])
        path = Path(artifact_dir) / f"{version}-baseline.joblib"
        joblib.dump({"model": model, "threshold": 0.5}, path)
        return [("baseline", {"strategy_return": 0.01}, str(path))]

    repository = FakeRepository(dataset, models)
    service = ArtifactRecoveryService(repository, str(tmp_path), trainer=fake_trainer)
    report = service.recover_all()

    assert calls == [{"baseline"}]
    assert report["recovered"] == 2
    assert report["audit"] == {"total": 2, "healthy": 2, "missing": 0, "invalid": 0}
    assert repository.session.commits == 1
    assert models[0].status == "CANDIDATE"
    assert models[1].status == "INACTIVE"
    assert all(Path(model.artifact_path).exists() for model in models)
    assert all(model.metrics["artifact_recovery_pipeline"] == RECOVERY_PIPELINE for model in models)


def test_recovery_is_idempotent_after_success(tmp_path):
    dataset = SimpleNamespace(
        id=1,
        symbol="ETHUSDT",
        version="dataset-test",
        rows=[{"features": {"a": 0.0}, "label": 0, "future_return": 0.0}],
        feature_names=["a"],
        train_size=80,
        metadata_json={},
    )
    path = tmp_path / "healthy.joblib"
    classifier = DummyClassifier(strategy="most_frequent").fit([[0.0], [1.0]], [0, 1])
    joblib.dump({"model": classifier, "threshold": 0.5}, path)
    model = SimpleNamespace(
        id=1,
        dataset_id=1,
        algorithm="baseline",
        version="model-v1",
        metrics={"artifact_recovery_pipeline": RECOVERY_PIPELINE},
        artifact_path=str(path),
        status="CANDIDATE",
    )

    def must_not_train(*args, **kwargs):
        raise AssertionError("artefato saudável não deve ser retreinado")

    service = ArtifactRecoveryService(FakeRepository(dataset, [model]), str(tmp_path), trainer=must_not_train)
    report = service.recover_all()

    assert report["recovered"] == 0
    assert report["already_healthy"] == 1
