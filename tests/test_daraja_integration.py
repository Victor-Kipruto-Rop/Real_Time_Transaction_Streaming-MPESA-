"""
Tests for Daraja OAuth Client and API

All tests use mocks - no actual API calls are made.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
import base64
from datetime import datetime, timedelta

from ingestion.daraja_client import DarajaClient, DarajaConfig


class TestDarajaConfig:
    """Test Daraja configuration dataclass"""

    def test_config_creation(self):
        """Test creating DarajaConfig"""
        config = DarajaConfig(
            environment='sandbox',
            consumer_key='test_key',
            consumer_secret='test_secret',
            business_shortcode='123456'
        )

        assert config.environment == 'sandbox'
        assert config.consumer_key == 'test_key'
        assert config.consumer_secret == 'test_secret'
        assert config.business_shortcode == '123456'

    def test_config_optional_fields(self):
        """Test DarajaConfig with optional fields"""
        config = DarajaConfig(
            environment='production',
            consumer_key='prod_key',
            consumer_secret='prod_secret',
            business_shortcode='999999',
            passkey='test_passkey',
            callback_url='https://example.com/callback'
        )

        assert config.passkey == 'test_passkey'
        assert config.callback_url == 'https://example.com/callback'


class TestDarajaClient:
    """Test Daraja API client"""

    @patch.dict(os.environ, {
        'DARAJA_ENVIRONMENT': 'sandbox',
        'DARAJA_CONSUMER_KEY': 'test_key',
        'DARAJA_CONSUMER_SECRET': 'test_secret',
        'MPESA_BUSINESS_SHORTCODE': '123456',
    }, clear=True)
    def test_from_env(self):
        """Test creating client from environment variables"""
        client = DarajaClient.from_env()

        assert client.environment == 'sandbox'
        assert client.consumer_key == 'test_key'
        assert client.consumer_secret == 'test_secret'
        assert client.business_shortcode == '123456'
        assert 'sandbox' in client.base_url

    @patch.dict(os.environ, {
        'DARAJA_ENVIRONMENT': 'production',
        'DARAJA_CONSUMER_KEY': 'prod_key',
        'DARAJA_CONSUMER_SECRET': 'prod_secret',
        'MPESA_BUSINESS_SHORTCODE': '999999',
    })
    def test_from_env_production(self):
        """Test creating production client from environment"""
        client = DarajaClient.from_env()

        assert client.environment == 'production'
        assert 'api.safaricom.co.ke' in client.base_url

    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_missing_credentials(self):
        """Test that ValueError is raised when credentials are missing"""
        with pytest.raises(ValueError):
            DarajaClient.from_env()

    @patch('ingestion.daraja_client.requests.Session.get')
    @patch.dict(os.environ, {
        'DARAJA_ENVIRONMENT': 'sandbox',
        'DARAJA_CONSUMER_KEY': 'test_key',
        'DARAJA_CONSUMER_SECRET': 'test_secret',
        'MPESA_BUSINESS_SHORTCODE': '123456',
    }, clear=True)
    def test_get_access_token_success(self, mock_session_get):
        """Test successful token generation"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'test_token_12345',
            'expires_in': 3600,
        }
        mock_session_get.return_value = mock_response

        client = DarajaClient.from_env()
        token = client.get_access_token()

        assert token == 'test_token_12345'
        assert client.access_token == 'test_token_12345'
        mock_session_get.assert_called_once()

    @patch('ingestion.daraja_client.requests.Session.get')
    @patch.dict(os.environ, {
        'DARAJA_ENVIRONMENT': 'sandbox',
        'DARAJA_CONSUMER_KEY': 'test_key',
        'DARAJA_CONSUMER_SECRET': 'test_secret',
        'MPESA_BUSINESS_SHORTCODE': '123456',
    })
    def test_get_access_token_caching(self, mock_session_get):
        """Test that valid tokens are cached"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'cached_token',
            'expires_in': 3600,
        }
        mock_session_get.return_value = mock_response

        client = DarajaClient.from_env()

        # First call
        token1 = client.get_access_token()
        # Second call (should use cache)
        token2 = client.get_access_token()

        # Mock should only be called once (caching works)
        assert mock_session_get.call_count == 1
        assert token1 == token2

    @patch('ingestion.daraja_client.requests.Session.get')
    @patch.dict(os.environ, {
        'DARAJA_ENVIRONMENT': 'sandbox',
        'DARAJA_CONSUMER_KEY': 'test_key',
        'DARAJA_CONSUMER_SECRET': 'test_secret',
        'MPESA_BUSINESS_SHORTCODE': '123456',
    })
    def test_get_access_token_failure(self, mock_session_get):
        """Test token generation failure"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = Exception('Unauthorized')
        mock_session_get.return_value = mock_response

        client = DarajaClient.from_env()

        with pytest.raises(Exception):
            client.get_access_token()

    @patch('ingestion.daraja_client.requests.Session.post')
    @patch('ingestion.daraja_client.requests.Session.get')
    @patch.dict(os.environ, {
        'DARAJA_ENVIRONMENT': 'sandbox',
        'DARAJA_CONSUMER_KEY': 'test_key',
        'DARAJA_CONSUMER_SECRET': 'test_secret',
        'MPESA_BUSINESS_SHORTCODE': '123456',
        'C2B_VALIDATION_URL': 'https://example.com/validate',
        'C2B_CONFIRMATION_URL': 'https://example.com/confirm',
    })
    def test_c2b_register_url_success(self, mock_session_get, mock_session_post):
        """Test successful C2B URL registration"""
        # Mock token generation
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            'access_token': 'test_token',
            'expires_in': 3600,
        }
        mock_session_get.return_value = mock_token_response

        # Mock URL registration
        mock_reg_response = Mock()
        mock_reg_response.status_code = 200
        mock_reg_response.json.return_value = {
            'ResponseDescription': 'The service request has been accepted successfully',
            'ResponseCode': '0',
        }
        mock_session_post.return_value = mock_reg_response

        client = DarajaClient.from_env()
        result = client.c2b_register_url()

        assert result['ResponseCode'] == '0'
        mock_session_post.assert_called_once()

    @patch('ingestion.daraja_client.requests.Session.post')
    @patch('ingestion.daraja_client.requests.Session.get')
    @patch.dict(os.environ, {
        'DARAJA_ENVIRONMENT': 'sandbox',
        'DARAJA_CONSUMER_KEY': 'test_key',
        'DARAJA_CONSUMER_SECRET': 'test_secret',
        'MPESA_BUSINESS_SHORTCODE': '123456',
    }, clear=True)
    def test_c2b_register_url_missing_urls(self, mock_session_get, mock_session_post):
        """Test C2B registration fails when URLs are not provided"""
        # Mock token generation
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            'access_token': 'test_token',
            'expires_in': 3600,
        }
        mock_session_get.return_value = mock_token_response

        client = DarajaClient.from_env()

        with pytest.raises(ValueError):
            client.c2b_register_url()

    @patch('ingestion.daraja_client.requests.Session.post')
    @patch('ingestion.daraja_client.requests.Session.get')
    @patch.dict(os.environ, {
        'DARAJA_ENVIRONMENT': 'sandbox',
        'DARAJA_CONSUMER_KEY': 'test_key',
        'DARAJA_CONSUMER_SECRET': 'test_secret',
        'MPESA_BUSINESS_SHORTCODE': '123456',
        'MPESA_PASSKEY': 'test_passkey',
        'CALLBACK_URL': 'https://example.com/callback',
    })
    def test_initiate_stk_push_success(self, mock_session_get, mock_session_post):
        """Test successful STK push initiation"""
        # Mock token generation
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            'access_token': 'test_token',
            'expires_in': 3600,
        }
        mock_session_get.return_value = mock_token_response

        # Mock STK push response
        mock_stk_response = Mock()
        mock_stk_response.status_code = 200
        mock_stk_response.json.return_value = {
            'CheckoutRequestID': 'ws_CO_DMZ_12345',
            'CustomerMessage': 'Success',
            'ResponseCode': '0',
            'ResponseDescription': 'The request has been accepted for processing',
            'MerchantRequestID': 'mr_12345',
        }
        mock_session_post.return_value = mock_stk_response

        client = DarajaClient.from_env()
        result = client.initiate_stk_push(
            phone_number='254712345678',
            amount=1000,
        )

        assert 'CheckoutRequestID' in result
        assert result['ResponseCode'] == '0'
        mock_session_post.assert_called_once()

    @patch('ingestion.daraja_client.requests.Session.get')
    @patch.dict(os.environ, {
        'DARAJA_ENVIRONMENT': 'sandbox',
        'DARAJA_CONSUMER_KEY': 'test_key',
        'DARAJA_CONSUMER_SECRET': 'test_secret',
        'MPESA_BUSINESS_SHORTCODE': '123456',
        'MPESA_PASSKEY': 'test_passkey',
    })
    def test_initiate_stk_push_invalid_amount(self, mock_session_get):
        """Test STK push fails with invalid amount"""
        # Mock token generation
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            'access_token': 'test_token',
            'expires_in': 3600,
        }
        mock_session_get.return_value = mock_token_response

        client = DarajaClient.from_env()

        with pytest.raises(ValueError):
            client.initiate_stk_push(
                phone_number='254712345678',
                amount=-100,
            )

    @patch.dict(os.environ, {
        'DARAJA_ENVIRONMENT': 'sandbox',
        'DARAJA_CONSUMER_KEY': 'test_key',
        'DARAJA_CONSUMER_SECRET': 'test_secret',
        'MPESA_BUSINESS_SHORTCODE': '123456',
        'MPESA_PASSKEY': 'test_passkey',
    })
    def test_stk_password_generation(self):
        """Test STK password generation"""
        client = DarajaClient.from_env()
        timestamp = '20260518211500'
        password = client._stk_password(timestamp)

        # Password should be base64 encoded
        assert isinstance(password, str)
        assert len(password) > 0

        # Decode and verify content
        decoded = base64.b64decode(password).decode('utf-8')
        expected = f'123456test_passkey{timestamp}'
        assert decoded == expected

    @patch('ingestion.daraja_client.requests.Session.post')
    @patch('ingestion.daraja_client.requests.Session.get')
    @patch.dict(os.environ, {
        'DARAJA_ENVIRONMENT': 'sandbox',
        'DARAJA_CONSUMER_KEY': 'test_key',
        'DARAJA_CONSUMER_SECRET': 'test_secret',
        'MPESA_BUSINESS_SHORTCODE': '123456',
        'C2B_VALIDATION_URL': 'https://example.com/validate',
        'C2B_CONFIRMATION_URL': 'https://example.com/confirm',
    })
    def test_c2b_register_url_failure(self, mock_session_get, mock_session_post):
        """Test C2B registration failure handling"""
        # Mock token generation
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            'access_token': 'test_token',
            'expires_in': 3600,
        }
        mock_session_get.return_value = mock_token_response

        # Mock URL registration failure
        mock_reg_response = Mock()
        mock_reg_response.raise_for_status.side_effect = Exception('Registration failed')
        mock_session_post.return_value = mock_reg_response

        client = DarajaClient.from_env()

        with pytest.raises(Exception):
            client.c2b_register_url()
