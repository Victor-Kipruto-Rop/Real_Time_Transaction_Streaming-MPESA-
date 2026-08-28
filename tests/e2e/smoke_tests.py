"""Smoke tests for the staging deployment gate."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import uuid

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def _configure_smoke_env() -> None:
    settings.WEBHOOK_SIGNING_SECRET = "staging-smoke-secret"
    settings.REQUIRE_WEBHOOK_SIGNATURE = True


def _signature_for(payload: dict) -> str:
    canonical = json.dumps(payload, default=str)
    return hmac.new(
        settings.WEBHOOK_SIGNING_SECRET.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _client() -> TestClient:
    _configure_smoke_env()
    return TestClient(app)


def _parse_known_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--staging", action="store_true")
    parser.parse_known_args()
    return parser.parse_args()


def test_health_endpoint() -> None:
    client = _client()
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_stk_initiation_flow() -> None:
    client = _client()
    response = client.post(
        "/api/v1/transactions/initiate-stk",
        json={
            "phone_number": "254712345678",
            "amount": 100.0,
            "account_reference": "SMOKE-123",
            "description": "Smoke test",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["checkout_request_id"].startswith("ws_CO_")


def test_c2b_confirmation_accepts_valid_payload() -> None:
    client = _client()
    payload = {
        "TransID": f"SMOKE-C2B-{uuid.uuid4()}",
        "TransAmount": "2000",
        "MSISDN": "254712345678",
        "BillRefNumber": "SMOKE-REF-1",
        "TransTime": "20260613120000",
    }
    response = client.post(
        "/api/v1/webhooks/c2b/confirmation",
        json=payload,
        headers={"X-Safaricom-Signature": _signature_for(payload)},
    )
    assert response.status_code == 200
    assert response.json()["ResultCode"] == 0


if __name__ == "__main__":
    _parse_known_args()
    for test in [test_health_endpoint, test_stk_initiation_flow, test_c2b_confirmation_accepts_valid_payload]:
        test()
        print(f"PASS: {test.__name__}")
