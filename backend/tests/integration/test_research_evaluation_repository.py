from sqlalchemy import delete

from app.database import SessionLocal
from app.models.research import ResearchEvaluationRun
from app.repositories.research_repository import ResearchRepository


def test_research_evaluation_history_is_persisted() -> None:
    with SessionLocal() as session:
        session.execute(delete(ResearchEvaluationRun))
        session.commit()
        repository = ResearchRepository(session)
        run = ResearchEvaluationRun(
            symbol="BTCUSDT",
            interval="15m",
            status="COMPLETED",
            new_candles=778,
            required_candles=778,
            models_trained=6,
            metrics_summary={"xgboost": {"strategy_return": -0.01}},
        )
        repository.save(run)
        session.commit()

        history = repository.list_evaluation_runs(10)

        assert len(history) == 1
        assert history[0].id == run.id
        assert history[0].metrics_summary["xgboost"]["strategy_return"] == -0.01

        session.execute(delete(ResearchEvaluationRun))
        session.commit()
