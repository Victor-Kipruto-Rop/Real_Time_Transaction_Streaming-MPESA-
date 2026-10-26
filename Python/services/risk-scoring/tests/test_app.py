from fastapi.testclient import TestClient

from risk_scoring.app import app
from risk_scoring.engine import assess_transaction

client = TestClient(app)


def test_health_endpoints_are_live_and_ready():
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").json()["model_version"]


def test_assessment_returns_explainable_signal_without_payment_action():
    response = client.post(
        "/v1/risk/assess",
        json={
            "transaction": {
                "TransID": "TX-1",
                "TransAmount": "100.00",
                "TransTime": "20261026120000",
                "MSISDN": "254700000000",
                "BusinessShortCode": "123456",
            },
            "history": [],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"]["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert payload["decision"]["model_version"]
    assert payload["disclaimer"].startswith("Risk signal only")
    assert "payment" not in payload["decision"]


def test_invalid_threshold_is_rejected():
    response = client.post(
        "/v1/risk/assess",
        json={"transaction": {"TransID": "TX-1"}, "amount_threshold": -1},
    )
    assert response.status_code == 422


def test_engine_can_be_called_without_database_dependencies():
    result = assess_transaction({"TransID": "TX-2", "TransAmount": "10.00"})
    assert result.risk_score >= 0
    assert result.risk_score <= 1
