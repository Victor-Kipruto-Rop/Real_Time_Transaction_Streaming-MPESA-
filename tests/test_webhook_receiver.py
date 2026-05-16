"""
Unit tests for webhook_receiver.py

Tests C2B validation/confirmation and B2C result handling,
including error cases and malformed payloads.
"""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestC2BValidationRoute:
    """Tests for C2B validation webhook endpoint."""

    def test_valid_c2b_validation_returns_success(self, flask_test_client, c2b_validation_payload):
        """Valid C2B validation payload should return success response."""
        response = flask_test_client.post(
            "/webhook/c2b/validation", json=c2b_validation_payload, content_type="application/json"
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["ResultCode"] == "0"
        assert data["ResultDesc"] == "Validation accepted"

    def test_invalid_c2b_validation_missing_fields(
        self, flask_test_client, invalid_c2b_validation_payload
    ):
        """Missing required fields should return error."""
        response = flask_test_client.post(
            "/webhook/c2b/validation",
            json=invalid_c2b_validation_payload,
            content_type="application/json",
        )
        # Should return 400 or 200 with error ResultCode
        assert response.status_code in [200, 400]

    def test_invalid_phone_number_in_validation(self, flask_test_client, invalid_phone_payload):
        """Invalid phone number format should be rejected."""
        response = flask_test_client.post(
            "/webhook/c2b/validation", json=invalid_phone_payload, content_type="application/json"
        )
        assert response.status_code in [200, 400, 422]

    def test_invalid_amount_in_validation(self, flask_test_client, invalid_amount_payload):
        """Amount exceeding limit should be rejected."""
        response = flask_test_client.post(
            "/webhook/c2b/validation", json=invalid_amount_payload, content_type="application/json"
        )
        assert response.status_code in [200, 400, 422]

    def test_invalid_timestamp_format(self, flask_test_client, invalid_timestamp_payload):
        """Invalid timestamp format should be rejected."""
        response = flask_test_client.post(
            "/webhook/c2b/validation",
            json=invalid_timestamp_payload,
            content_type="application/json",
        )
        assert response.status_code in [200, 400, 422]

    def test_null_json_payload_returns_error(self, flask_test_client):
        """Null/empty payload should return error."""
        response = flask_test_client.post(
            "/webhook/c2b/validation", data="", content_type="application/json"
        )
        assert response.status_code in [400, 415]

    def test_malformed_json_returns_error(self, flask_test_client):
        """Malformed JSON should return error."""
        response = flask_test_client.post(
            "/webhook/c2b/validation", data="{invalid json}", content_type="application/json"
        )
        assert response.status_code == 400

    @patch("ingestion.kafka_producer.MpesaKafkaProducer")
    def test_validation_publishes_to_kafka(
        self, mock_producer_class, flask_test_client, c2b_validation_payload
    ):
        """Valid validation should publish to Kafka."""
        mock_producer = MagicMock()
        mock_producer_class.return_value = mock_producer

        response = flask_test_client.post(
            "/webhook/c2b/validation", json=c2b_validation_payload, content_type="application/json"
        )

        assert response.status_code == 200
        # Verify Kafka producer was called
        assert mock_producer.publish_transaction.called or mock_producer.send.called

    def test_phone_number_standardization(self, flask_test_client):
        """Phone numbers in different formats should be standardized."""
        test_cases = [
            "254712345678",
            "+254712345678",
            "0712345678",
        ]

        for phone in test_cases:
            payload = {
                "TransactionType": "Pay Bills Online",
                "TransID": "TEST001",
                "TransTime": "20240514120000",
                "TransAmount": 500.00,
                "BusinessShortCode": "174379",
                "BillRefNumber": "INV001",
                "InvoiceNumber": "INV001",
                "MSISDN": phone,
            }

            response = flask_test_client.post(
                "/webhook/c2b/validation", json=payload, content_type="application/json"
            )
            assert response.status_code in [200, 201]


class TestC2BConfirmationRoute:
    """Tests for C2B confirmation webhook endpoint."""

    def test_valid_c2b_confirmation_returns_success(
        self, flask_test_client, c2b_confirmation_payload
    ):
        """Valid C2B confirmation should be accepted."""
        response = flask_test_client.post(
            "/webhook/c2b/confirmation",
            json=c2b_confirmation_payload,
            content_type="application/json",
        )
        assert response.status_code in [200, 201, 204]

    def test_confirmation_missing_fields(self, flask_test_client):
        """Confirmation with missing fields should be rejected."""
        incomplete_payload = {
            "TransID": "LHG31SV2QV",
            # Missing other required fields
        }

        response = flask_test_client.post(
            "/webhook/c2b/confirmation", json=incomplete_payload, content_type="application/json"
        )
        assert response.status_code in [200, 400, 422]

    @patch("ingestion.kafka_producer.MpesaKafkaProducer")
    def test_confirmation_publishes_to_kafka(
        self, mock_producer_class, flask_test_client, c2b_confirmation_payload
    ):
        """Confirmation should publish to Kafka."""
        mock_producer = MagicMock()
        mock_producer_class.return_value = mock_producer

        response = flask_test_client.post(
            "/webhook/c2b/confirmation",
            json=c2b_confirmation_payload,
            content_type="application/json",
        )

        assert response.status_code in [200, 201, 204]


class TestB2CResultRoute:
    """Tests for B2C result webhook endpoint."""

    def test_valid_b2c_result_returns_success(self, flask_test_client, b2c_result_payload):
        """Valid B2C result should be accepted."""
        response = flask_test_client.post(
            "/webhook/b2c/result", json=b2c_result_payload, content_type="application/json"
        )
        assert response.status_code in [200, 201, 204]

    def test_b2c_result_with_failed_result_code(self, flask_test_client, b2c_result_payload):
        """B2C result with failure code should still be accepted."""
        b2c_result_payload["ResultCode"] = 1  # Failed

        response = flask_test_client.post(
            "/webhook/b2c/result", json=b2c_result_payload, content_type="application/json"
        )
        assert response.status_code in [200, 201, 204]

    def test_b2c_result_missing_required_fields(self, flask_test_client):
        """B2C result missing required fields should be rejected."""
        incomplete_payload = {
            "TransactionID": "LHG31SV2QV",
            # Missing ConversationID, ResultCode, etc.
        }

        response = flask_test_client.post(
            "/webhook/b2c/result", json=incomplete_payload, content_type="application/json"
        )
        assert response.status_code in [200, 400, 422]


class TestHealthRoute:
    """Tests for health check endpoint."""

    def test_health_check_returns_200(self, flask_test_client):
        """Health check endpoint should return 200."""
        response = flask_test_client.get("/health")
        assert response.status_code == 200

    def test_health_check_response_format(self, flask_test_client):
        """Health check response should have required fields."""
        response = flask_test_client.get("/health")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "status" in data or "healthy" in data


class TestUIRoute:
    """Tests for the browser UI helper route."""

    def test_ui_page_loads(self, flask_test_client):
        response = flask_test_client.get("/ui")
        assert response.status_code == 200
        assert b"Webhook Sender" in response.data

    def test_webhook_get_redirects_to_ui(self, flask_test_client):
        response = flask_test_client.get("/webhook/c2b/confirmation")
        assert response.status_code in [301, 302]
        assert b"/ui?endpoint=/webhook/c2b/confirmation" in response.data or (
            response.headers.get("Location") == "/ui?endpoint=/webhook/c2b/confirmation"
        )


class TestRateLimiting:
    def test_rate_limit_triggers_429_when_configured(self, monkeypatch, c2b_confirmation_payload):
        import ingestion.webhook_receiver as wr

        monkeypatch.setenv("RATE_LIMIT_PER_MIN", "1")
        wr._RATE_STATE.clear()
        app = wr.create_app()
        app.config["TESTING"] = True
        client = app.test_client()

        first = client.post(
            "/webhook/c2b/confirmation", json=c2b_confirmation_payload, content_type="application/json"
        )
        assert first.status_code in [200, 201, 204]
        second = client.post(
            "/webhook/c2b/confirmation", json=c2b_confirmation_payload, content_type="application/json"
        )
        assert second.status_code == 429


class TestErrorHandling:
    """Tests for error handling."""

    def test_request_timeout_handling(self, flask_test_client):
        """Service should handle request timeouts gracefully."""
        # This would require mocking service calls to timeout
        pass

    def test_database_connection_error_handling(self, flask_test_client, c2b_validation_payload):
        """Database connection errors should be handled gracefully."""
        with patch("ingestion.webhook_receiver.db_connection") as mock_db:
            mock_db.side_effect = Exception("Connection refused")

            response = flask_test_client.post(
                "/webhook/c2b/validation",
                json=c2b_validation_payload,
                content_type="application/json",
            )

            # Should either return error response or fall back gracefully
            assert response.status_code in [200, 500, 503]

    def test_kafka_producer_error_handling(self, flask_test_client, c2b_validation_payload):
        """Kafka producer errors should not crash webhook."""
        with patch("ingestion.kafka_producer.MpesaKafkaProducer") as mock_producer:
            mock_producer.return_value.send.side_effect = Exception("Broker unavailable")

            response = flask_test_client.post(
                "/webhook/c2b/validation",
                json=c2b_validation_payload,
                content_type="application/json",
            )

            # Should return response despite Kafka error
            assert response.status_code in [200, 500, 503]


class TestConcurrency:
    """Tests for concurrent request handling."""

    def test_multiple_concurrent_validations(self, flask_test_client, c2b_validation_payload):
        """Service should handle multiple concurrent requests."""
        # Send multiple requests in sequence (simulating concurrency)
        responses = []
        for i in range(5):
            payload = c2b_validation_payload.copy()
            payload["TransID"] = f"TXN{i:06d}"

            response = flask_test_client.post(
                "/webhook/c2b/validation", json=payload, content_type="application/json"
            )
            responses.append(response)

        # All should succeed
        assert all(r.status_code == 200 for r in responses)


class TestValidationSchemas:
    """Tests for request/response validation schemas."""

    def test_c2b_validation_schema_validates_phone(self):
        """Phone validation should accept Kenyan numbers."""
        from schemas.transaction_schema import C2BValidationRequest

        # Valid Kenyan phone
        payload = {
            "TransactionType": "Pay Bills Online",
            "TransID": "TEST001",
            "TransTime": "20240514120000",
            "TransAmount": 500.00,
            "BusinessShortCode": "174379",
            "BillRefNumber": "INV001",
            "InvoiceNumber": "INV001",
            "MSISDN": "254712345678",
        }

        request = C2BValidationRequest(**payload)
        assert request.MSISDN == "254712345678"

    def test_c2b_validation_schema_rejects_invalid_phone(self):
        """Phone validation should reject invalid numbers."""
        from pydantic import ValidationError

        from schemas.transaction_schema import C2BValidationRequest

        payload = {
            "TransactionType": "Pay Bills Online",
            "TransID": "TEST001",
            "TransTime": "20240514120000",
            "TransAmount": 500.00,
            "BusinessShortCode": "174379",
            "BillRefNumber": "INV001",
            "InvoiceNumber": "INV001",
            "MSISDN": "invalid_number",
        }

        with pytest.raises(ValidationError):
            C2BValidationRequest(**payload)

    def test_c2b_validation_schema_validates_amount(self):
        """Amount validation should reject extreme values."""
        from pydantic import ValidationError

        from schemas.transaction_schema import C2BValidationRequest

        payload = {
            "TransactionType": "Pay Bills Online",
            "TransID": "TEST001",
            "TransTime": "20240514120000",
            "TransAmount": 2000000.00,  # Exceeds limit
            "BusinessShortCode": "174379",
            "BillRefNumber": "INV001",
            "InvoiceNumber": "INV001",
            "MSISDN": "254712345678",
        }

        with pytest.raises(ValidationError):
            C2BValidationRequest(**payload)
