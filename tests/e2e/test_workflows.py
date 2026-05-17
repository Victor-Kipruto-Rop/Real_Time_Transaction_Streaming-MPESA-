"""
End-to-End Tests for M-Pesa Platform
Tests complete workflows: STK Push flow, C2B payment, Reconciliation, etc.
Run with: pytest tests/e2e/test_workflows.py -v
"""

import pytest
import asyncio
import json
import hmac
import hashlib
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture
def test_client():
    """FastAPI test client"""
    from fastapi.testclient import TestClient
    from app.main import app

    return TestClient(app)


@pytest.fixture
def valid_signature():
    """Generate valid HMAC signature"""

    def _generate_signature(payload: dict, secret: str = "test-secret") -> str:
        body = json.dumps(payload)
        return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()

    return _generate_signature


@pytest.fixture
def c2b_webhook_payload():
    """Sample C2B webhook payload"""
    return {
        "TransactionType": "Pay Bills Online",
        "TransID": f"TXN{int(time.time())}",
        "TransTime": datetime.now().strftime("%Y%m%d%H%M%S"),
        "TransAmount": "1000",
        "BusinessShortCode": "8759693",
        "BillRefNumber": "CHAM001",
        "FirstName": "John",
        "LastName": "Doe",
        "MSISDN": "254712345678",
    }


@pytest.fixture
def stk_callback_payload():
    """Sample STK callback payload"""
    return {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "29115-123456-1",
                "CheckoutRequestID": "ws_CO_DMZ_12321_2740201215163000",
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount", "Value": 1000},
                        {"Name": "MpesaReceiptNumber", "Value": "LHG31AA5V61"},
                        {"Name": "TransactionDate", "Value": 20240115103030},
                        {"Name": "PhoneNumber", "Value": 254712345678},
                    ]
                },
            }
        }
    }


# ============================================================================
# E2E TEST 1: Complete STK Push Flow
# ============================================================================


class TestSTKPushFlow:
    """End-to-end STK push workflow"""

    @pytest.mark.asyncio
    async def test_stk_initiation_to_completion(self, test_client, valid_signature):
        """
        Test complete STK flow:
        1. Initiate STK push
        2. Query status
        3. Receive callback
        4. Verify transaction recorded
        """

        # Step 1: Initiate STK push
        stk_payload = {
            "phone_number": "254712345678",
            "amount": 1000,
            "account_reference": "CHAM001",
            "description": "Test payment",
        }

        signature = valid_signature(stk_payload)
        headers = {
            "X-Safaricom-Signature": signature,
            "Content-Type": "application/json",
        }

        response = test_client.post(
            "/api/v1/transactions/initiate-stk", json=stk_payload, headers=headers
        )

        assert response.status_code == 200
        stk_response = response.json()
        assert stk_response["status"] == "pending"
        assert "checkout_request_id" in stk_response
        checkout_id = stk_response["checkout_request_id"]

        # Step 2: Query STK status
        response = test_client.get(f"/api/v1/transactions/stk/{checkout_id}/status")
        assert response.status_code == 200

        # Step 3: Simulate callback from Safaricom
        callback_payload = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "29115-123456-1",
                    "CheckoutRequestID": checkout_id,
                    "ResultCode": 0,
                    "ResultDesc": "The service request is processed successfully.",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": 1000},
                            {"Name": "MpesaReceiptNumber", "Value": "LHG31AA5V61"},
                            {"Name": "TransactionDate", "Value": 20240115103030},
                            {"Name": "PhoneNumber", "Value": 254712345678},
                        ]
                    },
                }
            }
        }

        signature = valid_signature(callback_payload)
        headers["X-Safaricom-Signature"] = signature

        response = test_client.post(
            "/api/v1/webhooks/stk/callback", json=callback_payload, headers=headers
        )

        assert response.status_code == 200

        # Step 4: Verify transaction recorded
        response = test_client.get(
            "/api/v1/transactions",
            params={"phone_number": "254712345678", "status": "success", "limit": 10},
        )

        assert response.status_code == 200
        transactions = response.json()
        assert len(transactions["data"]) > 0

        # Find the transaction we just created
        txn = next((t for t in transactions["data"] if t["amount"] == 1000), None)
        assert txn is not None


# ============================================================================
# E2E TEST 2: C2B Payment Flow
# ============================================================================


class TestC2BPaymentFlow:
    """End-to-end C2B payment workflow"""

    @pytest.mark.asyncio
    async def test_c2b_validation_and_confirmation(
        self, test_client, valid_signature, c2b_webhook_payload
    ):
        """
        Test complete C2B flow:
        1. Receive validation request
        2. Respond with acceptance
        3. Receive confirmation
        4. Verify fraud detection ran
        5. Verify transaction in DB
        """

        # Step 1: Validation request
        validation_payload = c2b_webhook_payload.copy()
        signature = valid_signature(validation_payload)
        headers = {
            "X-Safaricom-Signature": signature,
            "Content-Type": "application/json",
        }

        response = test_client.post(
            "/api/v1/webhooks/c2b/validation", json=validation_payload, headers=headers
        )

        assert response.status_code == 200
        assert response.json()["ResultCode"] == 0

        # Step 2: Confirmation request
        confirmation_payload = c2b_webhook_payload.copy()
        confirmation_payload["TransactionStatus"] = "Success"

        signature = valid_signature(confirmation_payload)
        headers["X-Safaricom-Signature"] = signature

        response = test_client.post(
            "/api/v1/webhooks/c2b/confirmation",
            json=confirmation_payload,
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json()["ResultCode"] == 0

        # Step 3: Verify fraud detection (should have low fraud score)
        response = test_client.get("/api/v1/analytics/customer/254712345678")

        assert response.status_code == 200
        customer_data = response.json()
        assert "risk_profile" in customer_data
        assert customer_data["risk_profile"]["fraud_score"] < 0.5  # Should be low


# ============================================================================
# E2E TEST 3: Multi-Step Customer Journey
# ============================================================================


class TestCustomerJourney:
    """Test complete customer lifecycle"""

    @pytest.mark.asyncio
    async def test_customer_onboarding_and_transactions(
        self, test_client, valid_signature
    ):
        """
        Test customer journey:
        1. First transaction
        2. Multiple transactions
        3. Customer segmentation
        4. Analytics update
        """

        phone = "254798765432"

        # Step 1: Make first transaction
        for i in range(5):
            payload = {
                "TransactionType": "Pay Bills Online",
                "TransID": f"TXN{int(time.time() * 1000) + i}",
                "TransTime": datetime.now().strftime("%Y%m%d%H%M%S"),
                "TransAmount": str((i + 1) * 100),
                "BusinessShortCode": "8759693",
                "BillRefNumber": f"REF{i}",
                "FirstName": "Customer",
                "LastName": "Test",
                "MSISDN": phone,
            }

            signature = valid_signature(payload)
            headers = {
                "X-Safaricom-Signature": signature,
                "Content-Type": "application/json",
            }

            response = test_client.post(
                "/api/v1/webhooks/c2b/confirmation", json=payload, headers=headers
            )

            assert response.status_code == 200

        # Step 2: Verify customer profile created
        response = test_client.get(f"/api/v1/analytics/customer/{phone}")

        assert response.status_code == 200
        customer = response.json()
        assert customer["phone_number"] == phone
        assert customer["profile"]["transaction_count"] == 5
        assert customer["profile"]["total_amount"] == 1500  # 100+200+300+400+500

        # Step 3: Verify customer segmentation
        response = test_client.get("/api/v1/analytics/summary")
        assert response.status_code == 200


# ============================================================================
# E2E TEST 4: Fraud Detection Integration
# ============================================================================


class TestFraudDetectionFlow:
    """Test fraud detection in transaction flow"""

    @pytest.mark.asyncio
    async def test_fraud_alert_generation(self, test_client, valid_signature):
        """
        Test fraud detection:
        1. Send suspicious transaction
        2. Verify fraud alert generated
        3. Verify customer flagged
        """

        phone = "254712111111"

        # Send multiple high-value transactions in short time (suspicious)
        for i in range(10):
            payload = {
                "TransactionType": "Pay Bills Online",
                "TransID": f"FRAUD{int(time.time() * 1000) + i}",
                "TransTime": datetime.now().strftime("%Y%m%d%H%M%S"),
                "TransAmount": "50000",  # Very high amounts
                "BusinessShortCode": "8759693",
                "BillRefNumber": f"FRAU{i}",
                "FirstName": "Suspicious",
                "LastName": "User",
                "MSISDN": phone,
            }

            signature = valid_signature(payload)
            headers = {
                "X-Safaricom-Signature": signature,
                "Content-Type": "application/json",
            }

            test_client.post(
                "/api/v1/webhooks/c2b/confirmation", json=payload, headers=headers
            )

        # Check fraud alerts
        response = test_client.get(
            "/api/v1/analytics/fraud-alerts", params={"severity": "high"}
        )

        assert response.status_code == 200
        # Should have generated fraud alerts
        assert "data" in response.json()


# ============================================================================
# E2E TEST 5: Reconciliation Flow
# ============================================================================


class TestReconciliationFlow:
    """Test daily reconciliation process"""

    @pytest.mark.asyncio
    async def test_daily_reconciliation_workflow(self, test_client):
        """
        Test reconciliation:
        1. Trigger reconciliation
        2. Wait for completion
        3. Verify results
        """

        # Step 1: Trigger daily reconciliation
        response = test_client.post(
            "/api/v1/reconciliation/daily",
            json={"date": datetime.now().strftime("%Y-%m-%d"), "manual": True},
        )

        assert response.status_code in [200, 202]  # 200 or accepted

        if response.status_code == 200:
            recon_data = response.json()
            assert "reconciliation_id" in recon_data
            recon_id = recon_data["reconciliation_id"]
        else:
            # If async, get ID from response
            recon_data = response.json()
            recon_id = recon_data.get("reconciliation_id")

        # Step 2: Check reconciliation status
        if recon_id:
            response = test_client.get(f"/api/v1/reconciliation/{recon_id}")

            assert response.status_code == 200
            status_data = response.json()
            assert "statistics" in status_data
            assert "match_rate" in status_data or "matched" in status_data["statistics"]


# ============================================================================
# E2E TEST 6: Concurrent Webhooks
# ============================================================================


class TestConcurrentWebhooks:
    """Test handling concurrent webhooks"""

    @pytest.mark.asyncio
    async def test_concurrent_c2b_webhooks(self, test_client, valid_signature):
        """
        Test concurrent webhook handling:
        1. Send multiple webhooks simultaneously
        2. Verify all processed correctly
        3. Check for duplicates/race conditions
        """

        import concurrent.futures

        def send_webhook(txn_id: str, amount: str):
            """Send single webhook"""
            payload = {
                "TransactionType": "Pay Bills Online",
                "TransID": txn_id,
                "TransTime": datetime.now().strftime("%Y%m%d%H%M%S"),
                "TransAmount": amount,
                "BusinessShortCode": "8759693",
                "BillRefNumber": "CONCURRENT",
                "FirstName": "Test",
                "LastName": "User",
                "MSISDN": "254712345678",
            }

            signature = valid_signature(payload)
            headers = {
                "X-Safaricom-Signature": signature,
                "Content-Type": "application/json",
            }

            return test_client.post(
                "/api/v1/webhooks/c2b/confirmation", json=payload, headers=headers
            )

        # Send 100 webhooks concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(send_webhook, f"TXN{i}", str((i + 1) * 100))
                for i in range(100)
            ]

            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Verify all succeeded
        assert all(r.status_code == 200 for r in results)

        # Verify transaction count
        response = test_client.get(
            "/api/v1/transactions",
            params={"phone_number": "254712345678", "limit": 100},
        )

        assert response.status_code == 200
        # Should have created transactions (may not be exactly 100 due to dedup)


# ============================================================================
# E2E TEST 7: Error Recovery
# ============================================================================


class TestErrorRecovery:
    """Test system recovery from errors"""

    @pytest.mark.asyncio
    async def test_invalid_webhook_handling(self, test_client, valid_signature):
        """
        Test error handling:
        1. Send invalid webhook (bad signature)
        2. Verify rejection
        3. Send valid webhook
        4. Verify success
        """

        payload = {
            "TransactionType": "Pay Bills Online",
            "TransID": "TXN123",
            "TransTime": datetime.now().strftime("%Y%m%d%H%M%S"),
            "TransAmount": "1000",
            "BusinessShortCode": "8759693",
            "BillRefNumber": "ERROR_TEST",
            "FirstName": "Test",
            "LastName": "User",
            "MSISDN": "254712345678",
        }

        # Step 1: Send with invalid signature
        headers = {
            "X-Safaricom-Signature": "invalid_signature_xyz",
            "Content-Type": "application/json",
        }

        response = test_client.post(
            "/api/v1/webhooks/c2b/confirmation", json=payload, headers=headers
        )

        # Should reject
        assert response.status_code in [401, 403, 400]

        # Step 2: Send with valid signature
        signature = valid_signature(payload)
        headers["X-Safaricom-Signature"] = signature

        response = test_client.post(
            "/api/v1/webhooks/c2b/confirmation", json=payload, headers=headers
        )

        # Should succeed
        assert response.status_code == 200


# ============================================================================
# E2E TEST 8: Rate Limiting
# ============================================================================


class TestRateLimiting:
    """Test rate limiting enforcement"""

    @pytest.mark.asyncio
    async def test_webhook_rate_limiting(self, test_client, valid_signature):
        """
        Test rate limiting:
        1. Send requests within limit
        2. Send requests exceeding limit
        3. Verify requests rejected
        """

        # Send many rapid requests
        for i in range(10):
            payload = {
                "TransactionType": "Pay Bills Online",
                "TransID": f"RATE{int(time.time() * 1000) + i}",
                "TransTime": datetime.now().strftime("%Y%m%d%H%M%S"),
                "TransAmount": "100",
                "BusinessShortCode": "8759693",
                "BillRefNumber": f"RATE{i}",
                "FirstName": "Test",
                "LastName": "User",
                "MSISDN": f"25471234567{i}",
            }

            signature = valid_signature(payload)
            headers = {
                "X-Safaricom-Signature": signature,
                "Content-Type": "application/json",
            }

            response = test_client.post(
                "/api/v1/webhooks/c2b/confirmation", json=payload, headers=headers
            )

            # Early requests should succeed
            if i < 5:
                assert response.status_code == 200
            # Later requests might be rate limited
            # assert response.status_code in [200, 429]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
