"""
Pytest configuration and fixtures for M-Pesa transaction streaming tests.

Provides:
- Mock Kafka producer/consumer
- Mock database connections
- Flask test client
- Sample transaction payloads
- Temporary test databases
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import app components
try:
    from ingestion.webhook_receiver import app as flask_app
except ImportError:
    flask_app = None

try:
    from ingestion.daraja_client import DarajaClient
except ImportError:
    DarajaClient = None

try:
    from ingestion.kafka_producer import MpesaKafkaProducer
except ImportError:
    MpesaKafkaProducer = None


# =====================================================================
# Fixtures for Flask App Testing
# =====================================================================


@pytest.fixture
def flask_test_client():
    """Create Flask test client for webhook testing."""
    if not flask_app:
        pytest.skip("Flask app not available")
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client


@pytest.fixture
def app_context():
    """Provide Flask application context."""
    if not flask_app:
        pytest.skip("Flask app not available")
    with flask_app.app_context():
        yield flask_app


# =====================================================================
# Sample Transaction Payloads
# =====================================================================


@pytest.fixture
def c2b_validation_payload() -> Dict[str, Any]:
    """Sample C2B validation callback payload from Safaricom."""
    return {
        "TransactionType": "Pay Bills Online",
        "TransID": "LHG31SV2QV",
        "TransTime": "20240514120000",
        "TransAmount": 500.00,
        "BusinessShortCode": "174379",
        "BillRefNumber": "INV001",
        "InvoiceNumber": "INV001",
        "OrgAccountBalance": 10000.00,
        "ThirdPartyTransID": "3rd-party-123",
        "MSISDN": "254712345678",
        "FirstName": "John",
        "MiddleName": "Peter",
        "LastName": "Doe",
    }


@pytest.fixture
def c2b_confirmation_payload() -> Dict[str, Any]:
    """Sample C2B confirmation callback payload."""
    return {
        "TransactionType": "Pay Bills Online",
        "TransID": "LHG31SV2QV",
        "TransTime": "20240514120000",
        "TransAmount": 500.00,
        "BusinessShortCode": "174379",
        "BillRefNumber": "INV001",
        "InvoiceNumber": "INV001",
        "OrgAccountBalance": 9500.00,
        "MSISDN": "254712345678",
        "FirstName": "John",
    }


@pytest.fixture
def b2c_result_payload() -> Dict[str, Any]:
    """Sample B2C result callback payload."""
    return {
        "OriginatorConversationID": "12345-1234567-1",
        "ConversationID": "AG_20240514_1a1234567a89a1a1a1a1",
        "TransactionID": "LHG31SV2QV",
        "ResultCode": 0,
        "ResultDesc": "The service request has been processed successfully.",
        "OriginatorPartyChargesProceedingAmount": 50.00,
        "ReceiverPartyPublicName": "Jane Recipient",
        "TransactionAmount": 500.00,
        "TransactionReceipt": "LHG31SV2QV",
        "B2CUtilityAccountAvailableFunds": 50000.00,
        "B2CWorkingAccountAvailableFunds": 45000.00,
    }


@pytest.fixture
def stk_push_payload() -> Dict[str, Any]:
    """Sample STK push callback payload."""
    return {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "16813-1590513-1",
                "CheckoutRequestID": "ws_CO_DMZ_12321_2738256c6228c",
                "ResultCode": 0,
                "ResultDesc": "The service request has been processed successfully.",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount", "Value": 1},
                        {"Name": "MpesaReceiptNumber", "Value": "LHG31SV2QV"},
                        {"Name": "TransactionDate", "Value": 20240514120000},
                        {"Name": "PhoneNumber", "Value": 254712345678},
                    ]
                },
            }
        }
    }


@pytest.fixture
def invalid_c2b_validation_payload() -> Dict[str, Any]:
    """Invalid C2B payload (missing required fields)."""
    return {
        "TransactionType": "Pay Bills Online",
        # Missing TransID, TransTime, etc.
        "TransAmount": 500.00,
    }


@pytest.fixture
def invalid_phone_payload() -> Dict[str, Any]:
    """Payload with invalid phone number."""
    return {
        "TransactionType": "Pay Bills Online",
        "TransID": "LHG31SV2QV",
        "TransTime": "20240514120000",
        "TransAmount": 500.00,
        "BusinessShortCode": "174379",
        "BillRefNumber": "INV001",
        "InvoiceNumber": "INV001",
        "MSISDN": "invalid_phone_123",  # Invalid format
    }


@pytest.fixture
def invalid_amount_payload() -> Dict[str, Any]:
    """Payload with invalid transaction amount."""
    return {
        "TransactionType": "Pay Bills Online",
        "TransID": "LHG31SV2QV",
        "TransTime": "20240514120000",
        "TransAmount": 2000000.00,  # Exceeds max limit (1M KES)
        "BusinessShortCode": "174379",
        "BillRefNumber": "INV001",
        "InvoiceNumber": "INV001",
        "MSISDN": "254712345678",
    }


@pytest.fixture
def invalid_timestamp_payload() -> Dict[str, Any]:
    """Payload with invalid timestamp format."""
    return {
        "TransactionType": "Pay Bills Online",
        "TransID": "LHG31SV2QV",
        "TransTime": "2024-05-14 12:00:00",  # Wrong format
        "TransAmount": 500.00,
        "BusinessShortCode": "174379",
        "BillRefNumber": "INV001",
        "InvoiceNumber": "INV001",
        "MSISDN": "254712345678",
    }


# =====================================================================
# Mock Kafka Fixtures
# =====================================================================


@pytest.fixture
def mock_kafka_producer():
    """Create mock Kafka producer."""
    producer = MagicMock()
    producer.send = MagicMock(return_value=MagicMock(get=MagicMock(return_value="success")))
    producer.flush = MagicMock()
    producer.close = MagicMock()
    return producer


@pytest.fixture
def mock_kafka_consumer():
    """Create mock Kafka consumer."""
    consumer = MagicMock()
    consumer.poll = MagicMock(return_value={})
    consumer.close = MagicMock()
    consumer.commit = MagicMock()
    return consumer


@pytest.fixture
def mock_kafka_topics():
    """Mock Kafka topic metadata."""
    return {
        "mpesa-transactions": ["topic_metadata"],
        "mpesa-fraud-alerts": ["topic_metadata"],
    }


# =====================================================================
# Mock Database Fixtures
# =====================================================================


@pytest.fixture
def mock_postgres_connection():
    """Create mock PostgreSQL connection."""
    conn = MagicMock()
    cursor = MagicMock()

    conn.cursor = MagicMock(return_value=cursor)
    conn.commit = MagicMock()
    conn.rollback = MagicMock()
    conn.close = MagicMock()

    cursor.execute = MagicMock()
    cursor.fetchall = MagicMock(return_value=[])
    cursor.fetchone = MagicMock(return_value=None)
    cursor.close = MagicMock()

    return conn


@pytest.fixture
def mock_connection_pool():
    """Create mock database connection pool."""
    pool = MagicMock()
    pool.getconn = MagicMock(return_value=mock_postgres_connection())
    pool.putconn = MagicMock()
    pool.closeall = MagicMock()
    return pool


@pytest.fixture
def temp_db_file():
    """Create temporary SQLite database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


# =====================================================================
# Mock Daraja API Fixtures
# =====================================================================


@pytest.fixture
def mock_daraja_oauth_response() -> Dict[str, Any]:
    """Mock successful OAuth2 token response from Daraja."""
    return {
        "access_token": "test_access_token_123abc",
        "token_type": "Bearer",
        "expires_in": 3600,
    }


@pytest.fixture
def mock_daraja_c2b_register_response() -> Dict[str, Any]:
    """Mock successful C2B URL registration response."""
    return {
        "ConversationID": "AG_20240514_1a1234567a89a1a1a1a1",
        "OriginatorConversationID": "12345-1234567-1",
        "ResponseDescription": "success",
        "ResponseCode": "0",
    }


@pytest.fixture
def mock_daraja_stk_push_response() -> Dict[str, Any]:
    """Mock successful STK push initiation response."""
    return {
        "MerchantRequestID": "16813-1590513-1",
        "CheckoutRequestID": "ws_CO_DMZ_12321_2738256c6228c",
        "ResponseDescription": "Success. Request accepted for processing",
        "ResponseCode": "0",
        "CustomerMessage": "Enter your M-Pesa PIN to complete this transaction.",
    }


@pytest.fixture
def mock_daraja_stk_push_error_response() -> Dict[str, Any]:
    """Mock failed STK push response."""
    return {
        "requestId": None,
        "errorCode": "500.001.1001",
        "errorMessage": "Invalid access token",
    }


@pytest.fixture
def mock_daraja_client():
    """Create mock Daraja API client."""
    if not DarajaClient:
        pytest.skip("DarajaClient not available")
    client = MagicMock(spec=DarajaClient)
    client.get_access_token = MagicMock(return_value="test_token_123")
    client.initiate_stk_push = MagicMock(
        return_value={"ResponseCode": "0", "CheckoutRequestID": "test_checkout_id"}
    )
    client.c2b_register_url = MagicMock(return_value={"ResponseCode": "0"})
    return client


# =====================================================================
# Environment & Configuration Fixtures
# =====================================================================


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables."""
    env_vars = {
        "DARAJA_KEY": "test_key",
        "DARAJA_SECRET": "test_secret",
        "DARAJA_BASE_URL": "https://sandbox.safaricom.co.ke",
        "BUSINESS_SHORTCODE": "174379",
        "WEBHOOK_URL": "https://example.com/webhook",
        "KAFKA_BROKERS": "localhost:9092",
        "KAFKA_TOPIC_TRANSACTIONS": "mpesa-transactions",
        "KAFKA_TOPIC_ALERTS": "mpesa-fraud-alerts",
        "KAFKA_CONSUMER_GROUP": "mpesa-test-group",
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "mpesa_test",
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_password",
        "LOG_LEVEL": "INFO",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars


# =====================================================================
# Utility Fixtures
# =====================================================================


@pytest.fixture
def random_transaction_id():
    """Generate random transaction ID."""
    import uuid

    return str(uuid.uuid4())[:12].upper()


@pytest.fixture
def current_timestamp():
    """Get current timestamp in Daraja format."""
    return datetime.now().strftime("%Y%m%d%H%M%S")


@pytest.fixture
def kenyan_phone_numbers():
    """Various valid Kenyan phone number formats."""
    return [
        "254712345678",  # Standard format
        "+254712345678",  # International format
        "0712345678",  # Local format
        "254722345678",  # Different prefix
        "254702345678",  # Another prefix
    ]


@pytest.fixture
def sample_transaction_batch() -> list:
    """Create batch of sample transactions for batch testing."""
    return [
        {
            "TransID": f"TXN{i:06d}",
            "MSISDN": f"25471234{i:04d}",
            "TransAmount": 100 + (i * 50),
            "TransTime": "20240514120000",
            "BillRefNumber": f"INV{i:04d}",
        }
        for i in range(1, 11)
    ]


# =====================================================================
# Cleanup Fixtures
# =====================================================================


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Cleanup after each test."""
    yield
    # Reset mocks and clear temporary files
    import gc

    gc.collect()
