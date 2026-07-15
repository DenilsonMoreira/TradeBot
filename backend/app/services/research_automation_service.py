import logging
from datetime import UTC, datetime, timedelta

from app.ai.registry import ModelRegistry
from app.models.research import ResearchEvaluationRun
from app.repositories.candle_repository import CandleRepository
from app.repositories.research_repository import ResearchRepository
from app.services.dataset_service import DatasetService
from app.services.training_service import TrainingService
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService


logger = logging.getLogger(__name__)


class ResearchAutomationService:
    def __init__(
        self,
        candles: CandleRepository,
        research: ResearchRepository,
        datasets: DatasetService,
        training: TrainingService,
        registry: ModelRegistry,
        notifications: NotificationService | None = None,
        audit: AuditService | None = None,
        recipient: str = "",
    ) -> None:
        self.candles = candles
        self.research = research
        self.datasets = datasets
        self.training = training
        self.registry = registry
        self.notifications = notifications
        self.audit = audit
        self.recipient = recipient

    def get_market_status(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int,
        horizon: int,
        minimum_new_candles: int = 0,
    ) -> dict:
        latest = self.research.get_latest_dataset(symbol, interval, horizon)
        if latest is None:
            available = self.candles.count(symbol, interval)
            required = max(limit, minimum_new_candles)
            last_evaluated_at = None
        else:
            last_evaluated_at = datetime.fromisoformat(
                latest.rows[-1]["open_time"]
            )
            available = self.candles.count_after(
                symbol,
                interval,
                last_evaluated_at,
            )
            required = max(
                latest.test_size + horizon,
                minimum_new_candles,
            )

        missing = max(0, required - available)
        estimated_ready_at = None
        interval_seconds = _interval_seconds(interval)
        if missing and interval_seconds is not None:
            estimated_ready_at = (
                datetime.now(UTC) + timedelta(seconds=missing * interval_seconds)
            ).isoformat()
        return {
            "symbol": symbol.upper(),
            "interval": interval,
            "due": available >= required,
            "available_new_candles": available,
            "required_new_candles": required,
            "missing_candles": missing,
            "progress_percent": min(100.0, available / max(required, 1) * 100),
            "last_evaluated_at": (
                last_evaluated_at.isoformat()
                if last_evaluated_at is not None
                else None
            ),
            "estimated_ready_at": estimated_ready_at,
            "dataset_id": latest.id if latest is not None else None,
        }

    def evaluate_market(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int,
        horizon: int,
        train_ratio: float,
        minimum_new_candles: int = 0,
        promote_qualified: bool = False,
    ) -> dict:
        latest = self.research.get_latest_dataset(symbol, interval, horizon)
        result = {
            **self.get_market_status(
                symbol,
                interval,
                limit=limit,
                horizon=horizon,
                minimum_new_candles=minimum_new_candles,
            ),
            "trained_models": 0,
            "recommended": None,
            "activated": None,
            "evaluation_run_id": None,
        }
        if not result["due"]:
            return result

        run = ResearchEvaluationRun(
            symbol=symbol.upper(),
            interval=interval,
            status="RUNNING",
            new_candles=result["available_new_candles"],
            required_candles=result["required_new_candles"],
            models_trained=0,
            metrics_summary={},
        )
        self.research.save(run)
        self.research.session.commit()
        self.research.session.refresh(run)
        result["evaluation_run_id"] = run.id

        try:
            dataset = self.datasets.build(
                symbol,
                interval,
                limit,
                horizon,
                train_ratio,
            )
            run.dataset_id = dataset.id
            if latest is not None and dataset.id == latest.id:
                result["due"] = False
                self._finish_run(run, "SKIPPED")
                return result

            models = self.training.train(dataset.id)
            recommended = self.registry.recommend(
                dataset.id,
                min_strategy_return=0.0,
                min_f1=0.5,
                min_roc_auc=0.55,
                min_trade_count=20,
                min_walk_forward_return=0.0,
                min_profitable_folds=2,
                require_outperform_buy_hold=True,
            )
            activated = None
            if promote_qualified and recommended is not None:
                activated = self.registry.promote(recommended.id)

            result.update({
                "dataset_id": dataset.id,
                "trained_models": len(models),
                "recommended": recommended.algorithm if recommended else None,
                "activated": activated.algorithm if activated else None,
            })
            run.models_trained = len(models)
            run.recommended_algorithm = result["recommended"]
            run.activated_algorithm = result["activated"]
            run.metrics_summary = {
                model.algorithm: {
                    key: model.metrics.get(key)
                    for key in (
                        "strategy_return",
                        "walk_forward_return",
                        "walk_forward_profitable_folds",
                        "walk_forward_folds",
                        "trade_count",
                    )
                }
                for model in models
                if model.algorithm != "baseline"
            }
            self._finish_run(run, "COMPLETED")
            self._record_completed(run)
            return result
        except Exception as error:
            run.error_message = str(error)[:500]
            self._finish_run(run, "FAILED")
            self._record_failed(run)
            raise

    def _finish_run(self, run: ResearchEvaluationRun, status: str) -> None:
        run.status = status
        run.completed_at = datetime.now(UTC)
        self.research.session.commit()
        self.research.session.refresh(run)

    def _record_completed(self, run: ResearchEvaluationRun) -> None:
        if run.activated_algorithm:
            title = f"Modelo ativado para {run.symbol}"
            message = f"{run.activated_algorithm} foi aprovado e ativado após a avaliação quantitativa."
            severity = "info"
        elif run.recommended_algorithm:
            title = f"Novo candidato para {run.symbol}"
            message = f"{run.recommended_algorithm} passou nos critérios, mas não foi ativado automaticamente."
            severity = "info"
        else:
            title = f"Avaliação concluída para {run.symbol}"
            message = "Nenhum modelo cumpriu todos os critérios de promoção."
            severity = "warning"
        self._safe_records(run, severity, title, message, "completed")

    def _record_failed(self, run: ResearchEvaluationRun) -> None:
        self._safe_records(
            run,
            "critical",
            f"Falha na avaliação de {run.symbol}",
            run.error_message or "A avaliação quantitativa falhou.",
            "failed",
        )

    def _safe_records(
        self,
        run: ResearchEvaluationRun,
        severity: str,
        title: str,
        message: str,
        outcome: str,
    ) -> None:
        try:
            if self.notifications is not None and self.recipient:
                self.notifications.create(
                    self.recipient,
                    severity,
                    "research",
                    title,
                    message,
                    resource_id=str(run.id),
                )
            if self.audit is not None:
                self.audit.record(
                    "system:trainer-worker",
                    f"research_evaluation_{outcome}",
                    "research_evaluation",
                    resource_id=str(run.id),
                    details={
                        "symbol": run.symbol,
                        "dataset_id": run.dataset_id,
                        "recommended": run.recommended_algorithm,
                        "activated": run.activated_algorithm,
                    },
                )
        except Exception:
            logger.exception(
                "Falha ao registrar notificação/auditoria evaluation_run=%s",
                run.id,
            )


def _interval_seconds(interval: str) -> int | None:
    units = {"m": 60, "h": 3600, "d": 86400}
    if len(interval) < 2 or interval[-1] not in units:
        return None
    try:
        return int(interval[:-1]) * units[interval[-1]]
    except ValueError:
        return None
