import hashlib
import json
from pathlib import Path

from app.ai.ensemble import evaluate_soft_voting
from app.models.research import TrainedModel
from app.repositories.research_repository import ResearchRepository


class EnsembleService:
    def __init__(self, repository: ResearchRepository, artifact_dir: str):
        self.repository = repository
        self.artifact_dir = artifact_dir

    def evaluate(
        self,
        dataset_id: int,
        *,
        model_ids: list[int] | None = None,
        threshold: float = 0.5,
    ) -> TrainedModel:
        dataset = self.repository.get_dataset(dataset_id)
        if dataset is None:
            raise ValueError("dataset não encontrado")

        if model_ids is None:
            members = [
                model
                for model in self.repository.get_models_for_dataset(dataset_id)
                if model.algorithm not in {"baseline", "ensemble_soft_voting"}
            ]
        else:
            members = list(self.repository.get_models_by_ids(model_ids))
            if len(members) != len(set(model_ids)):
                raise ValueError("um ou mais modelos não foram encontrados")
        if len(members) < 2:
            raise ValueError("ensemble requer ao menos dois modelos")
        if any(model.dataset_id != dataset_id for model in members):
            raise ValueError("todos os modelos devem pertencer ao mesmo dataset")

        member_ids = sorted(model.id for model in members)
        identity = json.dumps(
            {"members": member_ids, "threshold": threshold},
            sort_keys=True,
        )
        version = "ensemble-v1-" + hashlib.sha256(identity.encode()).hexdigest()[:16]
        existing = self.repository.get_model_by_identity(
            dataset_id,
            "ensemble_soft_voting",
            version,
        )
        if existing is not None:
            return existing

        rows = dataset.rows[dataset.train_size :]
        x_test = [
            [row["features"][name] for name in dataset.feature_names]
            for row in rows
        ]
        y_test = [row["label"] for row in rows]
        future_returns = [row["future_return"] for row in rows]
        metrics, _, weights = evaluate_soft_voting(
            [model.artifact_path for model in members],
            x_test,
            y_test,
            future_returns,
            threshold=threshold,
        )
        target = Path(self.artifact_dir)
        target.mkdir(parents=True, exist_ok=True)
        artifact_path = target / f"{dataset.version}-{version}.json"
        artifact_path.write_text(
            json.dumps(
                {
                    "type": "soft_voting",
                    "dataset_id": dataset_id,
                    "member_ids": member_ids,
                    "weights": weights,
                    "threshold": threshold,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        ensemble = TrainedModel(
            dataset_id=dataset_id,
            algorithm="ensemble_soft_voting",
            version=version,
            metrics={
                **metrics,
                "member_ids": member_ids,
                "weights": weights,
                "threshold": threshold,
                "evaluation_split": "temporal_test",
            },
            artifact_path=str(artifact_path),
        )
        try:
            self.repository.save(ensemble)
            self.repository.session.commit()
            self.repository.session.refresh(ensemble)
        except Exception:
            self.repository.session.rollback()
            raise
        return ensemble
