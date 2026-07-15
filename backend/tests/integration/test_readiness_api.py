from fastapi.testclient import TestClient

from app.api.main import app


def test_readiness_report_exposes_separate_release_gates() -> None:
    with TestClient(app) as client:
        response = client.get("/readiness/report")

    assert response.status_code == 200
    body = response.json()
    assert body["environment"] == "TESTNET"
    assert isinstance(body["local_stack_ready"], bool)
    assert isinstance(body["server_release_ready"], bool)
    assert isinstance(body["automatic_trading_ready"], bool)
    assert body["summary"]["total"] == len(body["checks"])
    check_ids = {item["id"] for item in body["checks"]}
    assert {
        "database_revision",
        "execution_round_trip",
        "campaign_approved",
        "active_model",
    }.issubset(check_ids)

