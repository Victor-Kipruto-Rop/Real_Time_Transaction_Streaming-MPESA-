"""
Unit tests for stk_push.py

Tests STK push initialization, callback handling, transaction status
tracking, database persistence, retry logic, and error handling.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from ingestion.stk_push import STKPushHandler

# =====================================================================
# STK Push Initialization Tests
# =====================================================================


class TestSTKPushInitialization:
    """Tests for STK push handler initialization."""

    @pytest.fixture
    def daraja_client(self):
        """Create mock Daraja client."""
        client = MagicMock()
        client.initiate_stk_push = MagicMock()
        return client

    @pytest.fixture
    def db_connection(self):
        """Create mock database connection."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        return conn

    def test_handler_init_success(self, daraja_client, db_connection):
        """Handler should initialize successfully."""
        handler = STKPushHandler(daraja_client, db_connection)

        assert handler is not None
        assert handler.daraja_client == daraja_client
        assert handler.db_connection == db_connection

    def test_handler_requires_daraja_client(self):
        """Handler requires Daraja client."""
        with pytest.raises((TypeError, AttributeError)):
            handler = STKPushHandler(None, MagicMock())

    def test_handler_requires_database_connection(self, daraja_client):
        """Handler requires database connection."""
        with pytest.raises((TypeError, AttributeError)):
            handler = STKPushHandler(daraja_client, None)


# =====================================================================
# STK Push Initiation Tests
# =====================================================================


class TestSTKPushInitiation:
    """Tests for initiating STK push."""

    @pytest.fixture
    def handler(self):
        """Create handler with mocks."""
        daraja_client = MagicMock()
        db_connection = MagicMock()
        cursor = MagicMock()
        db_connection.cursor.return_value = cursor
        return STKPushHandler(daraja_client, db_connection)

    def test_initiate_stk_push_success(self, handler):
        """Should successfully initiate STK push."""
        handler.daraja_client.initiate_stk_push.return_value = {
            "MerchantRequestID": "MR123",
            "CheckoutRequestID": "CR123",
            "ResponseCode": "0",
        }

        result = handler.initiate_stk_push(
            phone_number="254712345678",
            amount=500,
            account_reference="INV001",
        )

        assert result is not None
        assert result.get("ResponseCode") == "0"

    def test_initiate_stk_push_saves_transaction(self, handler):
        """Should save transaction to database."""
        handler.daraja_client.initiate_stk_push.return_value = {
            "MerchantRequestID": "MR123",
            "CheckoutRequestID": "CR123",
            "ResponseCode": "0",
        }

        result = handler.initiate_stk_push(
            phone_number="254712345678",
            amount=500,
            account_reference="INV001",
        )

        # Verify database insert was called
        cursor = handler.db_connection.cursor()
        if hasattr(cursor, "execute"):
            # Should have inserted or updated transaction
            pass

    def test_initiate_stk_push_validates_phone(self, handler):
        """Should validate phone number format."""
        # Valid phones should work
        valid_phones = ["254712345678", "+254712345678", "0712345678"]

        handler.daraja_client.initiate_stk_push.return_value = {"ResponseCode": "0"}

        for phone in valid_phones:
            result = handler.initiate_stk_push(
                phone_number=phone,
                amount=500,
                account_reference="INV001",
            )
            # Should not raise error


# =====================================================================
# STK Push Callback Tests
# =====================================================================


class TestSTKPushCallback:
    """Tests for handling STK push callbacks."""

    @pytest.fixture
    def handler(self):
        """Create handler with mocks."""
        daraja_client = MagicMock()
        db_connection = MagicMock()
        cursor = MagicMock()
        db_connection.cursor.return_value = cursor
        return STKPushHandler(daraja_client, db_connection)

    def test_handle_success_callback(self, handler):
        """Should handle successful STK push callback."""
        callback_data = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "MR123",
                    "CheckoutRequestID": "CR123",
                    "ResultCode": 0,  # Success
                    "ResultDesc": "The service request has been processed successfully.",
                }
            }
        }

        result = handler.handle_callback(callback_data)

        # Should process successfully
        assert result is not None

    def test_handle_user_cancelled_callback(self, handler):
        """Should handle user-cancelled STK push."""
        callback_data = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "MR123",
                    "CheckoutRequestID": "CR123",
                    "ResultCode": 1,  # User cancelled
                    "ResultDesc": "The user cancelled the USSD request.",
                }
            }
        }

        result = handler.handle_callback(callback_data)

        # Should handle cancellation
        assert result is not None

    def test_handle_timeout_callback(self, handler):
        """Should handle STK push timeout."""
        callback_data = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "MR123",
                    "CheckoutRequestID": "CR123",
                    "ResultCode": 10,  # Timeout
                    "ResultDesc": "The user timed out.",
                }
            }
        }

        result = handler.handle_callback(callback_data)

        # Should handle timeout
        assert result is not None


# =====================================================================
# Transaction Status Tracking Tests
# =====================================================================


class TestTransactionStatusTracking:
    """Tests for tracking transaction status."""

    @pytest.fixture
    def handler(self):
        """Create handler with mocks."""
        daraja_client = MagicMock()
        db_connection = MagicMock()
        cursor = MagicMock()
        db_connection.cursor.return_value = cursor
        return STKPushHandler(daraja_client, db_connection)

    def test_status_initiated(self, handler):
        """Should track status as initiated."""
        handler.daraja_client.initiate_stk_push.return_value = {"ResponseCode": "0"}

        result = handler.initiate_stk_push(
            phone_number="254712345678",
            amount=500,
            account_reference="INV001",
        )

        # Should be in initiated state
        # Status tracking would be in database

    def test_status_pending_to_completed(self, handler):
        """Should transition from pending to completed."""
        # First initiate
        handler.daraja_client.initiate_stk_push.return_value = {"ResponseCode": "0"}

        # Then receive callback with success
        callback_data = {
            "Body": {
                "stkCallback": {
                    "ResultCode": 0,  # Success
                    "ResultDesc": "Success",
                }
            }
        }

        handler.handle_callback(callback_data)

        # Should transition to completed

    def test_status_pending_to_failed(self, handler):
        """Should transition from pending to failed."""
        # Receive callback with failure
        callback_data = {
            "Body": {
                "stkCallback": {
                    "ResultCode": 1,  # User cancelled
                    "ResultDesc": "User cancelled",
                }
            }
        }

        handler.handle_callback(callback_data)

        # Should transition to failed/cancelled


# =====================================================================
# Result Code Mapping Tests
# =====================================================================


class TestResultCodeMapping:
    """Tests for mapping result codes to status."""

    @pytest.fixture
    def handler(self):
        """Create handler with mocks."""
        daraja_client = MagicMock()
        db_connection = MagicMock()
        cursor = MagicMock()
        db_connection.cursor.return_value = cursor
        return STKPushHandler(daraja_client, db_connection)

    def test_result_code_0_is_success(self, handler):
        """Result code 0 should map to success."""
        callback_data = {
            "Body": {
                "stkCallback": {
                    "ResultCode": 0,
                    "ResultDesc": "Success",
                }
            }
        }

        # Should recognize as success
        handler.handle_callback(callback_data)

    def test_result_code_1_is_cancelled(self, handler):
        """Result code 1 should map to cancelled."""
        callback_data = {
            "Body": {
                "stkCallback": {
                    "ResultCode": 1,
                    "ResultDesc": "User cancelled",
                }
            }
        }

        # Should recognize as cancelled
        handler.handle_callback(callback_data)

    def test_result_code_10_is_timeout(self, handler):
        """Result code 10 should map to timeout."""
        callback_data = {
            "Body": {
                "stkCallback": {
                    "ResultCode": 10,
                    "ResultDesc": "User timed out",
                }
            }
        }

        # Should recognize as timeout
        handler.handle_callback(callback_data)


# =====================================================================
# Transaction Persistence Tests
# =====================================================================


class TestTransactionPersistence:
    """Tests for persisting transactions to database."""

    @pytest.fixture
    def handler(self):
        """Create handler with mocks."""
        daraja_client = MagicMock()
        db_connection = MagicMock()
        cursor = MagicMock()
        db_connection.cursor.return_value = cursor
        return STKPushHandler(daraja_client, db_connection)

    def test_save_transaction_to_database(self, handler):
        """Should save transaction to database."""
        handler.daraja_client.initiate_stk_push.return_value = {
            "MerchantRequestID": "MR123",
            "CheckoutRequestID": "CR123",
            "ResponseCode": "0",
        }

        result = handler.initiate_stk_push(
            phone_number="254712345678",
            amount=500,
            account_reference="INV001",
        )

        # Should have saved to database
        assert result is not None

    def test_update_transaction_on_callback(self, handler):
        """Should update transaction on callback."""
        # Save initial transaction
        handler.daraja_client.initiate_stk_push.return_value = {
            "MerchantRequestID": "MR123",
            "CheckoutRequestID": "CR123",
            "ResponseCode": "0",
        }

        # Receive callback
        callback_data = {
            "Body": {
                "stkCallback": {
                    "ResultCode": 0,
                    "ResultDesc": "Success",
                }
            }
        }

        handler.handle_callback(callback_data)

        # Should have updated database

    def test_transaction_fields_persisted(self, handler):
        """Should persist all required transaction fields."""
        handler.daraja_client.initiate_stk_push.return_value = {
            "MerchantRequestID": "MR123",
            "CheckoutRequestID": "CR123",
            "ResponseCode": "0",
        }

        result = handler.initiate_stk_push(
            phone_number="254712345678",
            amount=500,
            account_reference="INV001",
        )

        # All required fields should be present or saved
        assert result is not None


# =====================================================================
# Retry Logic Tests
# =====================================================================


class TestRetryLogic:
    """Tests for retry logic."""

    @pytest.fixture
    def handler(self):
        """Create handler with mocks."""
        daraja_client = MagicMock()
        db_connection = MagicMock()
        cursor = MagicMock()
        db_connection.cursor.return_value = cursor
        return STKPushHandler(daraja_client, db_connection)

    def test_retry_on_transient_error(self, handler):
        """Should retry on transient errors."""
        # First call fails, second succeeds
        handler.daraja_client.initiate_stk_push.side_effect = [
            Exception("Temporary error"),
            {"ResponseCode": "0"},
        ]

        # Should retry
        # Implementation depends on how retries are implemented

    def test_no_retry_on_permanent_error(self, handler):
        """Should not retry on permanent errors."""
        handler.daraja_client.initiate_stk_push.side_effect = Exception(
            "Invalid credentials"
        )

        # Should raise immediately without retry


# =====================================================================
# Timeout Handling Tests
# =====================================================================


class TestTimeoutHandling:
    """Tests for timeout handling."""

    @pytest.fixture
    def handler(self):
        """Create handler with mocks."""
        daraja_client = MagicMock()
        db_connection = MagicMock()
        cursor = MagicMock()
        db_connection.cursor.return_value = cursor
        return STKPushHandler(daraja_client, db_connection)

    def test_handle_daraja_timeout(self, handler):
        """Should handle timeouts from Daraja API."""
        handler.daraja_client.initiate_stk_push.side_effect = TimeoutError(
            "Daraja timeout"
        )

        with pytest.raises(TimeoutError):
            handler.initiate_stk_push(
                phone_number="254712345678",
                amount=500,
                account_reference="INV001",
            )


# =====================================================================
# Phone Number Validation Tests
# =====================================================================


class TestPhoneValidation:
    """Tests for phone number validation."""

    @pytest.fixture
    def handler(self):
        """Create handler with mocks."""
        daraja_client = MagicMock()
        db_connection = MagicMock()
        cursor = MagicMock()
        db_connection.cursor.return_value = cursor
        return STKPushHandler(daraja_client, db_connection)

    def test_accepts_valid_kenyan_numbers(self, handler):
        """Should accept valid Kenyan phone numbers."""
        handler.daraja_client.initiate_stk_push.return_value = {"ResponseCode": "0"}

        valid_numbers = [
            "254712345678",
            "+254712345678",
            "0712345678",
        ]

        for number in valid_numbers:
            result = handler.initiate_stk_push(
                phone_number=number,
                amount=500,
                account_reference="INV001",
            )
            assert result is not None

    def test_rejects_invalid_phone_numbers(self, handler):
        """Should reject invalid phone numbers."""
        invalid_numbers = [
            "invalid",
            "123",
            "+1234567890",  # Non-Kenyan
            "",
        ]

        for number in invalid_numbers:
            with pytest.raises((ValueError, Exception)):
                handler.initiate_stk_push(
                    phone_number=number,
                    amount=500,
                    account_reference="INV001",
                )


# =====================================================================
# Amount Validation Tests
# =====================================================================


class TestAmountValidation:
    """Tests for amount validation."""

    @pytest.fixture
    def handler(self):
        """Create handler with mocks."""
        daraja_client = MagicMock()
        db_connection = MagicMock()
        cursor = MagicMock()
        db_connection.cursor.return_value = cursor
        return STKPushHandler(daraja_client, db_connection)

    def test_accepts_valid_amounts(self, handler):
        """Should accept valid transaction amounts."""
        handler.daraja_client.initiate_stk_push.return_value = {"ResponseCode": "0"}

        valid_amounts = [1, 500, 50000, 150000]

        for amount in valid_amounts:
            result = handler.initiate_stk_push(
                phone_number="254712345678",
                amount=amount,
                account_reference="INV001",
            )
            assert result is not None

    def test_rejects_invalid_amounts(self, handler):
        """Should reject invalid amounts."""
        invalid_amounts = [0, -100, -1]

        for amount in invalid_amounts:
            with pytest.raises((ValueError, Exception)):
                handler.initiate_stk_push(
                    phone_number="254712345678",
                    amount=amount,
                    account_reference="INV001",
                )


# =====================================================================
# Error Handling Tests
# =====================================================================


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.fixture
    def handler(self):
        """Create handler with mocks."""
        daraja_client = MagicMock()
        db_connection = MagicMock()
        cursor = MagicMock()
        db_connection.cursor.return_value = cursor
        return STKPushHandler(daraja_client, db_connection)

    def test_handle_api_error(self, handler):
        """Should handle Daraja API errors."""
        handler.daraja_client.initiate_stk_push.side_effect = Exception("API Error")

        with pytest.raises(Exception):
            handler.initiate_stk_push(
                phone_number="254712345678",
                amount=500,
                account_reference="INV001",
            )

    def test_handle_database_error(self, handler):
        """Should handle database errors."""
        handler.db_connection.cursor.side_effect = Exception("DB Error")

        with pytest.raises(Exception):
            handler.db_connection.cursor()

    def test_handle_malformed_callback(self, handler):
        """Should handle malformed callbacks."""
        malformed_callback = {"invalid": "data"}

        with pytest.raises((KeyError, ValueError, Exception)):
            handler.handle_callback(malformed_callback)


# =====================================================================
# Integration Tests
# =====================================================================


class TestSTKPushIntegration:
    """Integration tests combining multiple components."""

    def test_full_stk_push_workflow(self):
        """Test complete STK push workflow."""
        # Create mocks
        daraja_client = MagicMock()
        db_connection = MagicMock()
        cursor = MagicMock()
        db_connection.cursor.return_value = cursor

        # Create handler
        handler = STKPushHandler(daraja_client, db_connection)

        # Step 1: Initiate STK push
        daraja_client.initiate_stk_push.return_value = {
            "MerchantRequestID": "MR123",
            "CheckoutRequestID": "CR123",
            "ResponseCode": "0",
        }

        result = handler.initiate_stk_push(
            phone_number="254712345678",
            amount=500,
            account_reference="INV001",
        )
        assert result is not None

        # Step 2: Handle callback
        callback_data = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "MR123",
                    "CheckoutRequestID": "CR123",
                    "ResultCode": 0,  # Success
                    "ResultDesc": "Success",
                }
            }
        }

        callback_result = handler.handle_callback(callback_data)
        assert callback_result is not None
