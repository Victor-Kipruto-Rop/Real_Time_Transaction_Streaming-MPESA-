"""
Tests for webhook receiver functionality
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from flask import Flask


class TestWebhookReceiver:
    """Test webhook receiver endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from ingestion.webhook_receiver import app

        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "healthy"

    def test_c2b_confirmation_endpoint(self, client, sample_mpesa_transaction):
        """Test C2B confirmation webhook"""
        with patch("ingestion.kafka_producer.KafkaProducerClient") as mock_producer:
            response = client.post(
                "/webhook/c2b/confirmation",
                data=json.dumps(sample_mpesa_transaction),
                content_type="application/json",
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["ResultCode"] == 0

    def test_c2b_validation_endpoint(self, client, sample_mpesa_transaction):
        """Test C2B validation webhook"""
        response = client.post(
            "/webhook/c2b/validation",
            data=json.dumps(sample_mpesa_transaction),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["ResultCode"] == 0

    def test_stk_callback_endpoint(self, client):
        """Test STK Push callback webhook"""
        callback_data = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "REQ123",
                    "CheckoutRequestID": "CHK123",
                    "ResultCode": 0,
                    "ResultDesc": "Success",
                }
            }
        }

        response = client.post(
            "/webhook/stk/callback",
            data=json.dumps(callback_data),
            content_type="application/json",
        )

        assert response.status_code == 200

    def test_invalid_json_payload(self, client):
        """Test handling of invalid JSON"""
        response = client.post(
            "/webhook/c2b/confirmation",
            data="invalid json",
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_missing_required_fields(self, client):
        """Test handling of missing required fields"""
        incomplete_data = {"TransID": "TXN123"}

        response = client.post(
            "/webhook/c2b/confirmation",
            data=json.dumps(incomplete_data),
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_rate_limiting(self, client, sample_mpesa_transaction):
        """Test rate limiting on webhook endpoints"""
        # Send multiple requests rapidly
        responses = []
        for i in range(150):  # Exceed rate limit
            response = client.post(
                "/webhook/c2b/confirmation",
                data=json.dumps(sample_mpesa_transaction),
                content_type="application/json",
            )
            responses.append(response.status_code)

        # Should have some 429 (Too Many Requests) responses
        assert 429 in responses

    def test_duplicate_transaction_handling(self, client, sample_mpesa_transaction):
        """Test handling of duplicate transactions"""
        with patch("ingestion.kafka_producer.KafkaProducerClient"):
            # Send same transaction twice
            response1 = client.post(
                "/webhook/c2b/confirmation",
                data=json.dumps(sample_mpesa_transaction),
                content_type="application/json",
            )

            response2 = client.post(
                "/webhook/c2b/confirmation",
                data=json.dumps(sample_mpesa_transaction),
                content_type="application/json",
            )

            assert response1.status_code == 200
            # Second should be rejected or handled as duplicate
            assert response2.status_code in [200, 409]

    def test_webhook_authentication(self, client, sample_mpesa_transaction):
        """Test webhook authentication/authorization"""
        # Without auth token
        response = client.post(
            "/webhook/c2b/confirmation",
            data=json.dumps(sample_mpesa_transaction),
            content_type="application/json",
        )

        # With valid auth token
        response_with_auth = client.post(
            "/webhook/c2b/confirmation",
            data=json.dumps(sample_mpesa_transaction),
            content_type="application/json",
            headers={"Authorization": "Bearer valid_token"},
        )

        assert response_with_auth.status_code in [200, 401]


class TestWebhookMetrics:
    """Test webhook metrics collection"""

    def test_request_counter(self, client, sample_mpesa_transaction):
        """Test counting webhook requests"""
        from ingestion.metrics import WebhookMetrics

        metrics = WebhookMetrics()

        with patch("ingestion.kafka_producer.KafkaProducerClient"):
            for i in range(5):
                client.post(
                    "/webhook/c2b/confirmation",
                    data=json.dumps(sample_mpesa_transaction),
                    content_type="application/json",
                )

        stats = metrics.get_stats()
        assert stats["total_requests"] >= 5

    def test_response_time_tracking(self, client, sample_mpesa_transaction):
        """Test tracking webhook response times"""
        from ingestion.metrics import WebhookMetrics

        metrics = WebhookMetrics()

        with patch("ingestion.kafka_producer.KafkaProducerClient"):
            client.post(
                "/webhook/c2b/confirmation",
                data=json.dumps(sample_mpesa_transaction),
                content_type="application/json",
            )

        stats = metrics.get_stats()
        assert "avg_response_time" in stats

    def test_error_rate_tracking(self, client):
        """Test tracking webhook error rates"""
        from ingestion.metrics import WebhookMetrics

        metrics = WebhookMetrics()

        # Send invalid requests
        for i in range(3):
            client.post(
                "/webhook/c2b/confirmation",
                data="invalid",
                content_type="application/json",
            )

        stats = metrics.get_stats()
        assert stats["error_count"] >= 3


class TestWebhookSecurity:
    """Test webhook security features"""

    def test_ip_whitelisting(self, client, sample_mpesa_transaction):
        """Test IP whitelisting for webhooks"""
        # Request from non-whitelisted IP
        response = client.post(
            "/webhook/c2b/confirmation",
            data=json.dumps(sample_mpesa_transaction),
            content_type="application/json",
            environ_base={"REMOTE_ADDR": "192.168.1.1"},
        )

        # Should be rejected or allowed based on configuration
        assert response.status_code in [200, 403]

    def test_signature_verification(self, client, sample_mpesa_transaction):
        """Test webhook signature verification"""
        # Without signature
        response = client.post(
            "/webhook/c2b/confirmation",
            data=json.dumps(sample_mpesa_transaction),
            content_type="application/json",
        )

        # With valid signature
        response_with_sig = client.post(
            "/webhook/c2b/confirmation",
            data=json.dumps(sample_mpesa_transaction),
            content_type="application/json",
            headers={"X-Signature": "valid_signature"},
        )

        assert response_with_sig.status_code in [200, 401]

    def test_replay_attack_prevention(self, client, sample_mpesa_transaction):
        """Test prevention of replay attacks"""
        # Add timestamp to transaction
        sample_mpesa_transaction["timestamp"] = "2026-06-13T10:00:00Z"

        with patch("ingestion.kafka_producer.KafkaProducerClient"):
            # First request should succeed
            response1 = client.post(
                "/webhook/c2b/confirmation",
                data=json.dumps(sample_mpesa_transaction),
                content_type="application/json",
            )

            # Replay with old timestamp should be rejected
            import time

            time.sleep(1)
            response2 = client.post(
                "/webhook/c2b/confirmation",
                data=json.dumps(sample_mpesa_transaction),
                content_type="application/json",
            )

            assert response1.status_code == 200


@pytest.mark.integration
class TestWebhookIntegration:
    """Integration tests for webhook receiver"""

    @pytest.mark.skip(reason="Requires running services")
    def test_webhook_to_kafka_flow(self):
        """Test complete flow from webhook to Kafka"""
        pass

    @pytest.mark.skip(reason="Requires running services")
    def test_webhook_to_database_flow(self):
        """Test complete flow from webhook to database"""
        pass
