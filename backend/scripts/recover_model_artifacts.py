import json

from app.config import settings
from app.database import SessionLocal
from app.repositories.research_repository import ResearchRepository
from app.services.artifact_recovery_service import ArtifactRecoveryService


def main() -> None:
    with SessionLocal() as db:
        service = ArtifactRecoveryService(ResearchRepository(db), settings.model_artifact_dir)
        print(json.dumps({"before": service.audit()}, ensure_ascii=False), flush=True)
        report = service.recover_all(
            progress=lambda item: print(json.dumps(item, ensure_ascii=False), flush=True)
        )
        print(json.dumps({"result": report}, ensure_ascii=False), flush=True)
        if report["failed"] or report["audit"]["missing"] or report["audit"]["invalid"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
