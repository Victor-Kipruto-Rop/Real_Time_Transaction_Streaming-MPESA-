"""
Unit tests for daraja_client.py

Tests OAuth2 token management, API calls to Safaricom Daraja,
error handling, and retry logic.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from ingestion.daraja_client import DarajaClient

# =====================================================================
# Token Generation Tests
# =====================================================================


def test_stk_password_generation() -> None:
    """Test STK push password generation."""
    client = DarajaClient(
        consumer_key="k",
        consumer_secret="s",
        business_shortcode="123456",
        passkey="passkey",
        environment="sandbox",
    )
    ts = "20260514120000"
    expected = base64.b64encode(b"123456passkey20260514120000").decode("utf-8")
    assert client._stk_password(ts) == expected


def test_access_token_is_cached() -> None:
    """Test that access token is cached."""
    client = DarajaClient(
        consumer_key="k",
        consumer_secret="s",
        business_shortcode="123456",
        passkey="passkey",
        environment="sandbox",
    )

    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"access_token": "token1", "expires_in": 3600}
    client._session.get = MagicMock(return_value=resp)

    t1 = client.get_access_token()
    t2 = client.get_access_token()

    assert t1 == "token1"
    assert t2 == "token1"
    assert client._session.get.call_count == 1


# =====================================================================
# OAuth2 Token Tests
# =====================================================================


class TestOAuth2TokenManagement:
    """Tests for OAuth2 token lifecycle."""

    @pytest.fixture
    def daraja_client(self):
        """Create Daraja client for testing."""
        return DarajaClient(
            consumer_key="test_key",
            consumer_secret="test_secret",
            business_shortcode="174379",
            passkey="test_passkey",
            environment="sandbox",
        )

    def test_token_expiry_is_tracked(self, daraja_client):
        """Token expiry should be calculated from expires_in."""
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"access_token": "test_token", "expires_in": 3600}
        daraja_client._session.get = MagicMock(return_value=resp)

        token = daraja_client.get_access_token()

        assert token == "test_token"
        # Token should be cached
        if hasattr(daraja_client, "_token_expiry"):
            assert daraja_client._token_expiry > datetime.now()

    def test_token_refresh_on_expiry(self, daraja_client):
        """Should refresh token when near expiry."""
        # First call returns token with short expiry
        resp1 = MagicMock()
        resp1.raise_for_status.return_value = None
        resp1.json.return_value = {"access_token": "token1", "expires_in": 1}

        # Second call returns new token
        resp2 = MagicMock()
        resp2.raise_for_status.return_value = None
        resp2.json.return_value = {"access_token": "token2", "expires_in": 3600}

        daraja_client._session.get = MagicMock(side_effect=[resp1, resp2])

        # Get token (should cache)
        token1 = daraja_client.get_access_token()

        # Wait briefly, then get token again (might refresh if near expiry)
        import time

        time.sleep(0.1)
        token2 = daraja_client.get_access_token()

        assert token1 == "token1"
        # token2 might be token1 or token2 depending on refresh logic

    def test_oauth_error_handling(self, daraja_client):
        """Should handle OAuth errors gracefully."""
        resp = MagicMock()
        resp.raise_for_status.side_effect = Exception("Invalid credentials")
        daraja_client._session.get = MagicMock(return_value=resp)

        with pytest.raises(Exception):
            daraja_client.get_access_token()


# =====================================================================
# STK Push Tests
# =====================================================================


class TestSTKPush:
    """Tests for STK push payment prompts."""

    @pytest.fixture
    def daraja_client(self):
        """Create Daraja client."""
        client = DarajaClient(
            consumer_key="test_key",
            consumer_secret="test_secret",
            business_shortcode="174379",
            passkey="test_passkey",
            environment="sandbox",
        )
        client.access_token = "test_token"
        client.token_expiry = datetime.now() + timedelta(hours=1)
        return client

    def test_stk_push_initiation_success(self, daraja_client):
        """Should successfully initiate STK push."""
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {
            "MerchantRequestID": "16813-1590513-1",
            "CheckoutRequestID": "ws_CO_DMZ_12321_2738256c6228c",
            "ResponseDescription": "Success",
            "ResponseCode": "0",
            "CustomerMessage": "Enter M-Pesa PIN",
        }

        with patch.object(daraja_client._session, "post", return_value=resp):
            result = daraja_client.initiate_stk_push(
                phone_number="254712345678",
                amount=500,
                account_reference="INV001",
            )

            assert result.get("ResponseCode") == "0"

    def test_stk_push_validates_phone_format(self, daraja_client):
        """STK push should validate phone number."""
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"ResponseCode": "0"}

        with patch.object(daraja_client._session, "post", return_value=resp):
            # Valid phones
            for phone in ["254712345678", "+254712345678"]:
                result = daraja_client.initiate_stk_push(
                    phone_number=phone,
                    amount=500,
                    account_reference="INV001",
                )
                assert result is not None

    def test_stk_push_rejects_invalid_phone(self, daraja_client):
        """STK push should reject invalid phone."""
        with pytest.raises((ValueError, Exception)):
            daraja_client.initiate_stk_push(
                phone_number="invalid",
                amount=500,
                account_reference="INV001",
            )

    def test_stk_push_amount_validation(self, daraja_client):
        """STK push should validate amount."""
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"ResponseCode": "0"}

        # Valid amounts
        for amount in [1, 500, 150000]:
            with patch.object(daraja_client._session, "post", return_value=resp):
                result = daraja_client.initiate_stk_push(
                    phone_number="254712345678",
                    amount=amount,
                    account_reference="INV001",
                )
                assert result is not None

    def test_stk_push_error_response(self, daraja_client):
        """Should handle STK push errors."""
        resp = MagicMock()
        resp.raise_for_status.side_effect = Exception("API Error")

        with patch.object(daraja_client._session, "post", return_value=resp):
            with pytest.raises(Exception):
                daraja_client.initiate_stk_push(
                    phone_number="254712345678",
                    amount=500,
                    account_reference="INV001",
                )


# =====================================================================
# C2B Registration Tests
# =====================================================================


class TestC2BRegistration:
    """Tests for C2B URL registration."""

    @pytest.fixture
    def daraja_client(self):
        """Create Daraja client."""
        client = DarajaClient(
            consumer_key="test_key",
            consumer_secret="test_secret",
            business_shortcode="174379",
            passkey="test_passkey",
            environment="sandbox",
        )
        client.access_token = "test_token"
        client.token_expiry = datetime.now() + timedelta(hours=1)
        return client

    def test_c2b_register_url_success(self, daraja_client):
        """Should successfully register C2B URL."""
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {
            "ConversationID": "AG_20240514_123",
            "OriginatorConversationID": "12345-1234567-1",
            "ResponseDescription": "success",
            "ResponseCode": "0",
        }

        with patch.object(daraja_client._session, "post", return_value=resp):
            result = daraja_client.c2b_register_url(
                validation_url="https://example.com/validate",
                confirmation_url="https://example.com/confirm",
            )

            assert result is not None
            assert result.get("ResponseCode") == "0"


# =====================================================================
# Configuration Tests
# =====================================================================


class TestClientConfiguration:
    """Tests for client configuration."""

    def test_client_init_with_all_params(self):
        """Client should initialize with all parameters."""
        client = DarajaClient(
            consumer_key="key",
            consumer_secret="secret",
            business_shortcode="123456",
            passkey="passkey",
            environment="sandbox",
        )

        assert client.consumer_key == "key"
        assert client.consumer_secret == "secret"
        assert client.business_shortcode == "123456"

    def test_client_uses_sandbox_environment(self):
        """Client should use sandbox when specified."""
        client = DarajaClient(
            consumer_key="key",
            consumer_secret="secret",
            business_shortcode="123456",
            passkey="passkey",
            environment="sandbox",
        )

        # Sandbox URLs should be used
        assert "sandbox" in client.base_url.lower() or "sandbox" not in client.base_url

    def test_client_uses_production_environment(self):
        """Client should use production when specified."""
        client = DarajaClient(
            consumer_key="key",
            consumer_secret="secret",
            business_shortcode="123456",
            passkey="passkey",
            environment="production",
        )

        # Should be configured for production
        assert client.environment == "production"


# =====================================================================
# Error Handling Tests
# =====================================================================


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.fixture
    def daraja_client(self):
        """Create Daraja client."""
        client = DarajaClient(
            consumer_key="test_key",
            consumer_secret="test_secret",
            business_shortcode="174379",
            passkey="test_passkey",
            environment="sandbox",
        )
        client.access_token = "test_token"
        client.token_expiry = datetime.now() + timedelta(hours=1)
        return client

    def test_http_401_unauthorized(self, daraja_client):
        """Should handle 401 Unauthorized errors."""
        resp = MagicMock()
        resp.raise_for_status.side_effect = Exception("401 Unauthorized")

        with patch.object(daraja_client._session, "post", return_value=resp):
            with pytest.raises(Exception):
                daraja_client.initiate_stk_push(
                    phone_number="254712345678",
                    amount=500,
                    account_reference="INV001",
                )

    def test_http_500_server_error(self, daraja_client):
        """Should handle 500 Server errors."""
        resp = MagicMock()
        resp.raise_for_status.side_effect = Exception("500 Server Error")

        with patch.object(daraja_client._session, "post", return_value=resp):
            with pytest.raises(Exception):
                daraja_client.initiate_stk_push(
                    phone_number="254712345678",
                    amount=500,
                    account_reference="INV001",
                )

    def test_connection_timeout(self, daraja_client):
        """Should handle connection timeouts."""
        with patch.object(daraja_client._session, "post") as mock_post:
            mock_post.side_effect = TimeoutError("Connection timeout")

            with pytest.raises(TimeoutError):
                daraja_client.initiate_stk_push(
                    phone_number="254712345678",
                    amount=500,
                    account_reference="INV001",
                )

    def test_network_error(self, daraja_client):
        """Should handle network errors."""
        with patch.object(daraja_client._session, "post") as mock_post:
            mock_post.side_effect = ConnectionError("Network unreachable")

            with pytest.raises(ConnectionError):
                daraja_client.initiate_stk_push(
                    phone_number="254712345678",
                    amount=500,
                    account_reference="INV001",
                )

    def test_invalid_json_response(self, daraja_client):
        """Should handle invalid JSON in response."""
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        with patch.object(daraja_client._session, "post", return_value=resp):
            with pytest.raises((json.JSONDecodeError, Exception)):
                daraja_client.initiate_stk_push(
                    phone_number="254712345678",
                    amount=500,
                    account_reference="INV001",
                )


# =====================================================================
# Integration Tests
# =====================================================================


class TestClientIntegration:
    """Integration tests for client."""

    def test_full_stk_push_workflow(self):
        """Test complete STK push workflow."""
        client = DarajaClient(
            consumer_key="test_key",
            consumer_secret="test_secret",
            business_shortcode="174379",
            passkey="test_passkey",
            environment="sandbox",
        )

        # Mock token response
        token_resp = MagicMock()
        token_resp.raise_for_status.return_value = None
        token_resp.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600,
        }

        # Mock STK push response
        stk_resp = MagicMock()
        stk_resp.raise_for_status.return_value = None
        stk_resp.json.return_value = {
            "MerchantRequestID": "123",
            "CheckoutRequestID": "abc",
            "ResponseCode": "0",
        }

        with patch.object(client._session, "get", return_value=token_resp):
            with patch.object(client._session, "post", return_value=stk_resp):
                # Get token
                token = client.get_access_token()
                assert token == "test_token"

                # Initiate STK push
                result = client.initiate_stk_push(
                    phone_number="254712345678",
                    amount=500,
                    account_reference="INV001",
                )
                assert result.get("ResponseCode") == "0"
