"""
Pytest configuration and shared fixtures for M-Pesa Analytics Platform tests
"""

import os
import uuid

os.environ.setdefault("USE_SQLITE_FOR_TESTS", "1")

import pytest
from unittest.mock import Mock, MagicMock
from typing import Generator

from app.config import settings


@pytest.fixture(autouse=True)
def reset_security_settings():
    """Keep the singleton settings safe between tests."""
    original_secret = settings.WEBHOOK_SIGNING_SECRET
    original_require = settings.REQUIRE_WEBHOOK_SIGNATURE
    settings.WEBHOOK_SIGNING_SECRET = ""
    settings.REQUIRE_WEBHOOK_SIGNATURE = False
    yield
    settings.WEBHOOK_SIGNING_SECRET = original_secret
    settings.REQUIRE_WEBHOOK_SIGNATURE = original_require


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables for testing"""
    env_vars = {
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "mpesa_test",
        "POSTGRES_USER": "test_user",
        "POSTGRES_PASSWORD": "test_password",
        "KAFKA_BROKERS": "localhost:9092",
        "KAFKA_TOPIC_TRANSACTIONS": "test-transactions",
        "DARAJA_CONSUMER_KEY": "test_key",
        "DARAJA_CONSUMER_SECRET": "test_secret",
        "DARAJA_BUSINESS_SHORTCODE": "174379",
        "DARAJA_PASSKEY": "test_passkey",
        "DARAJA_ENVIRONMENT": "sandbox",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def mock_postgres_connection():
    """Mock PostgreSQL connection"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer"""
    mock_producer = MagicMock()
    mock_producer.send.return_value = MagicMock()
    return mock_producer


@pytest.fixture
def sample_mpesa_transaction():
    """Sample M-Pesa transaction data."""
    txn_id = f"TXN-{uuid.uuid4().hex[:16]}"
    return {
        "TransID": txn_id,
        "TransAmount": "1000.00",
        "MSISDN": "254712345678",
        "AccountReference": "ACC001",
        "TransTime": "20260613120000",
        "BillRefNumber": "BILL001",
        "FirstName": "John",
        "MiddleName": "Doe",
        "LastName": "Smith",
        "OrgAccountBalance": "50000.00",
    }


@pytest.fixture
def sample_stk_push_request():
    """Sample STK Push request data"""
    return {
        "phone_number": "254712345678",
        "amount": 100,
        "account_reference": "TEST001",
        "transaction_desc": "Test Payment",
    }


@pytest.fixture
def mock_daraja_oauth_response():
    """Mock Daraja OAuth token response"""
    return {"access_token": "mock_access_token_12345", "expires_in": "3599"}


@pytest.fixture
def mock_rds_iam_token():
    """Mock RDS IAM authentication token"""
    return "mock_rds_iam_token_abcdef123456"


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    """Path to docker-compose file for integration tests"""
    return os.path.join(pytestconfig.rootdir, "docker-compose.yml")


@pytest.fixture
def client():
    """Shared Flask test client fixture."""
    from ingestion import webhook_receiver
    from ingestion.webhook_receiver import app

    app.config["TESTING"] = True
    webhook_receiver._RATE_STATE.clear()
    webhook_receiver._REPLAY_CACHE.clear()
    with app.test_client() as test_client:
        yield test_client
