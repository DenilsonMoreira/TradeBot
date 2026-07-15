import asyncio
import logging

from app.ai.registry import ModelRegistry
from app.config import settings
from app.database import SessionLocal
from app.repositories.candle_repository import CandleRepository
from app.repositories.research_repository import ResearchRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.audit_repository import AuditRepository
from app.services.dataset_service import DatasetService
from app.services.research_automation_service import ResearchAutomationService
from app.services.training_service import TrainingService
from app.services.notification_service import NotificationService
from app.services.audit_service import AuditService


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def run_cycle() -> list[dict]:
    results = []
    symbols = [item.strip().upper() for item in settings.candle_symbols.split(",")]
    intervals = [item.strip() for item in settings.candle_intervals.split(",")]
    with SessionLocal() as session:
        candles = CandleRepository(session)
        research = ResearchRepository(session)
        service = ResearchAutomationService(
            candles,
            research,
            DatasetService(candles, research),
            TrainingService(research, settings.model_artifact_dir),
            ModelRegistry(research),
            NotificationService(NotificationRepository(session)),
            AuditService(AuditRepository(session)),
            settings.auth_operator_email,
        )
        for symbol in filter(None, symbols):
            for interval in filter(None, intervals):
                try:
                    result = service.evaluate_market(
                        symbol,
                        interval,
                        limit=settings.research_dataset_limit,
                        horizon=settings.research_horizon,
                        train_ratio=settings.research_train_ratio,
                        minimum_new_candles=(
                            settings.research_minimum_new_candles
                        ),
                        promote_qualified=settings.research_promote_qualified,
                    )
                    results.append(result)
                    logger.info("Avaliação de pesquisa: %s", result)
                except Exception:
                    logger.exception(
                        "Falha na pesquisa symbol=%s interval=%s",
                        symbol,
                        interval,
                    )
    return results


async def run_worker() -> None:
    logger.info(
        "Trainer worker iniciado enabled=%s promote=%s",
        settings.research_automation_enabled,
        settings.research_promote_qualified,
    )
    while True:
        if settings.research_automation_enabled:
            run_cycle()
        await asyncio.sleep(
            max(60, settings.research_evaluation_interval_seconds)
        )


if __name__ == "__main__":
    asyncio.run(run_worker())
