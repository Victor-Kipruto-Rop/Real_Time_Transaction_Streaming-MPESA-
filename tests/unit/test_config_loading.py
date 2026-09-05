import hashlib
import hmac
import json
import os
import uuid

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("USE_SQLITE_FOR_TESTS", "1")

from app.config import Settings, settings
from app.main import app


def test_settings():
    print("Testing Configuration Loading:")
    print(f"DATABASE_URL: {settings.DATABASE_URL}")
    print(f"KAFKA_BROKERS: {settings.KAFKA_BROKERS}")
    print(f"GRAFANA_URL: {settings.GRAFANA_URL}")
    print(f"UI_TOKEN: {settings.UI_TOKEN}")

    assert settings.POSTGRES_HOST == "localhost"
    assert settings.KAFKA_BROKERS == "localhost:9092"
    assert settings.UI_TOKEN in {"set_me_via_env", ""}
    print("Settings test passed!")


def test_rejects_insecure_default_secrets():
    with pytest.raises(ValueError, match="non-default|placeholder|secret"):
        Settings(
            POSTGRES_PASSWORD="admin123",
            SECRET_KEY="change_me",
            WEBHOOK_SIGNING_SECRET="default-secret",
            GRAFANA_ADMIN_PASSWORD="admin123",
        )


def test_explicit_real_secret_enables_signature_enforcement(monkeypatch):
    monkeypatch.delenv("WEBHOOK_SIGNING_SECRET", raising=False)
    monkeypatch.delenv("REQUIRE_WEBHOOK_SIGNATURE", raising=False)
    monkeypatch.setenv("WEBHOOK_SIGNING_SECRET", "real-secret-123")
    monkeypatch.setenv("REQUIRE_WEBHOOK_SIGNATURE", "true")

    import app.config as config_module
    import importlib

    importlib.reload(config_module)

    assert config_module.settings.WEBHOOK_SIGNING_SECRET == "real-secret-123"
    assert config_module.settings.REQUIRE_WEBHOOK_SIGNATURE is True


def test_webhook_signature_is_canonical_and_order_independent():
    settings.WEBHOOK_SIGNING_SECRET = "canonical-signature-secret"
    settings.REQUIRE_WEBHOOK_SIGNATURE = True
    transaction_id = f"TXN-ORDER-{uuid.uuid4()}"

    payload = {
        "b": 2,
        "a": 1,
        "TransID": transaction_id,
        "TransAmount": "2000",
        "MSISDN": "254712345678",
        "BillRefNumber": f"SMOKE-REF-{uuid.uuid4().hex[:8]}",
        "TransTime": "20260613120000",
    }
    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True, default=str)
    signature = hmac.new(
        settings.WEBHOOK_SIGNING_SECRET.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    client = TestClient(app)
    response = client.post(
        "/api/v1/webhooks/c2b/confirmation",
        json=payload,
        headers={"X-Safaricom-Signature": signature},
    )

    assert response.status_code == 200


if __name__ == "__main__":
    test_settings()
