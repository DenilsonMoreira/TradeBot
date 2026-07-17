import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from app.ai.artifact_validation import validate_model_artifact
from app.ai.trainer import train_candidates
from app.models.research import DatasetArtifact, TrainedModel
from app.repositories.research_repository import ResearchRepository


RECOVERY_PIPELINE = "model-v4-walk-forward-purged-recovery-v1"
Trainer = Callable[..., list[tuple[str, dict, str]]]


class ArtifactRecoveryService:
    def __init__(self, research: ResearchRepository, artifact_dir: str, trainer: Trainer = train_candidates):
        self.research = research
        self.artifact_dir = Path(artifact_dir)
        self.trainer = trainer

    def audit(self) -> dict:
        models = list(self.research.list_all_models())
        healthy = 0
        missing = 0
        invalid = 0
        for model in models:
            valid, reason = validate_model_artifact(model.artifact_path)
            if valid:
                healthy += 1
            elif reason == "arquivo ausente ou vazio":
                missing += 1
            else:
                invalid += 1
        return {"total": len(models), "healthy": healthy, "missing": missing, "invalid": invalid}

    def recover_all(self, progress: Callable[[dict], None] | None = None) -> dict:
        datasets = list(self.research.list_all_datasets())
        report = {"datasets": len(datasets), "processed": 0, "recovered": 0, "already_healthy": 0, "failed": []}
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        for dataset in datasets:
            try:
                result = self._recover_dataset(dataset)
                report["processed"] += 1
                report["recovered"] += result["recovered"]
                report["already_healthy"] += result["already_healthy"]
                self.research.session.commit()
                if progress:
                    progress({"dataset_id": dataset.id, "symbol": dataset.symbol, **result})
            except Exception as error:
                self.research.session.rollback()
                failure = {"dataset_id": dataset.id, "symbol": dataset.symbol, "error": str(error)}
                report["failed"].append(failure)
                if progress:
                    progress(failure)
        report["audit"] = self.audit()
        return report

    def _recover_dataset(self, dataset: DatasetArtifact) -> dict:
        models = list(self.research.get_models_for_dataset(dataset.id))
        if not models:
            return {"models": 0, "recovered": 0, "already_healthy": 0}
        sample = [dataset.rows[0]["features"][name] for name in dataset.feature_names]
        to_recover = []
        healthy = 0
        for model in models:
            valid, _ = validate_model_artifact(model.artifact_path, sample)
            recovery_current = model.metrics.get("artifact_recovery_pipeline") == RECOVERY_PIPELINE
            if valid and recovery_current:
                healthy += 1
            else:
                to_recover.append(model)
        if not to_recover:
            return {"models": len(models), "recovered": 0, "already_healthy": healthy}

        algorithms = {model.algorithm for model in to_recover}
        unsupported = algorithms - {"baseline", "logistic_regression", "random_forest", "xgboost", "lightgbm", "catboost"}
        if unsupported:
            raise ValueError(f"algoritmos não suportados na recuperação: {sorted(unsupported)}")
        canonical_version = f"{dataset.version}-{RECOVERY_PIPELINE}"
        results = self.trainer(
            dataset.rows,
            dataset.feature_names,
            dataset.train_size,
            str(self.artifact_dir),
            canonical_version,
            algorithms=algorithms,
            holding_period=int(dataset.metadata_json.get("horizon", 1)),
            cost_rate=float(dataset.metadata_json.get("evaluation_cost_rate_per_side", 0.0015)),
        )
        by_algorithm = {name: (metrics, path) for name, metrics, path in results}
        recovered_at = datetime.now(UTC).isoformat()
        for model in to_recover:
            if model.algorithm not in by_algorithm:
                raise ValueError(f"treino não retornou {model.algorithm}")
            metrics, source_path = by_algorithm[model.algorithm]
            target = self.artifact_dir / Path(model.artifact_path).name
            temporary = target.with_suffix(target.suffix + ".tmp")
            shutil.copyfile(source_path, temporary)
            temporary.replace(target)
            valid, reason = validate_model_artifact(str(target), sample)
            if not valid:
                raise ValueError(f"artefato {model.id} inválido após recuperação: {reason}")
            model.artifact_path = str(target)
            model.metrics = {
                **metrics,
                "artifact_recovered_at": recovered_at,
                "artifact_recovery_pipeline": RECOVERY_PIPELINE,
                "original_model_version": model.version,
            }
        for _, source_path in by_algorithm.values():
            Path(source_path).unlink(missing_ok=True)
        return {"models": len(models), "recovered": len(to_recover), "already_healthy": healthy}
