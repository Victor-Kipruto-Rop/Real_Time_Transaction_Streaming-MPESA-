"""
Tests for Daraja API integration
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from ingestion.daraja_client import DarajaClient
from ingestion.mpesa_transactions import MPesaTransactionHandler


class TestDarajaClient:
    """Test Daraja API client functionality"""
    
    def test_oauth_token_generation(self, mock_env_vars, mock_daraja_oauth_response):
        """Test OAuth token generation"""
        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = mock_daraja_oauth_response
            mock_get.return_value.status_code = 200
            
            client = DarajaClient()
            token = client.get_access_token()
            
            assert token == 'mock_access_token_12345'
            mock_get.assert_called_once()
    
    def test_oauth_token_caching(self, mock_env_vars, mock_daraja_oauth_response):
        """Test that OAuth tokens are cached"""
        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = mock_daraja_oauth_response
            mock_get.return_value.status_code = 200
            
            client = DarajaClient()
            token1 = client.get_access_token()
            token2 = client.get_access_token()
            
            assert token1 == token2
            # Should only call API once due to caching
            assert mock_get.call_count == 1
    
    def test_c2b_register_urls(self, mock_env_vars, mock_daraja_oauth_response):
        """Test C2B URL registration"""
        with patch('requests.get') as mock_get, \
             patch('requests.post') as mock_post:
            mock_get.return_value.json.return_value = mock_daraja_oauth_response
            mock_get.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                'ResponseCode': '0',
                'ResponseDescription': 'Success'
            }
            mock_post.return_value.status_code = 200
            
            client = DarajaClient()
            result = client.register_c2b_urls(
                validation_url='https://example.com/validate',
                confirmation_url='https://example.com/confirm'
            )
            
            assert result['ResponseCode'] == '0'
            mock_post.assert_called_once()
    
    def test_stk_push_request(self, mock_env_vars, mock_daraja_oauth_response, sample_stk_push_request):
        """Test STK Push request"""
        with patch('requests.get') as mock_get, \
             patch('requests.post') as mock_post:
            mock_get.return_value.json.return_value = mock_daraja_oauth_response
            mock_get.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                'MerchantRequestID': 'REQ123',
                'CheckoutRequestID': 'CHK123',
                'ResponseCode': '0',
                'ResponseDescription': 'Success'
            }
            mock_post.return_value.status_code = 200
            
            client = DarajaClient()
            result = client.stk_push(**sample_stk_push_request)
            
            assert result['ResponseCode'] == '0'
            assert 'CheckoutRequestID' in result
            mock_post.assert_called_once()
    
    def test_oauth_error_handling(self, mock_env_vars):
        """Test OAuth error handling"""
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 401
            mock_get.return_value.json.return_value = {'error': 'invalid_credentials'}
            
            client = DarajaClient()
            with pytest.raises(Exception):
                client.get_access_token()
    
    def test_api_timeout_handling(self, mock_env_vars):
        """Test API timeout handling"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = TimeoutError('Request timeout')
            
            client = DarajaClient()
            with pytest.raises(TimeoutError):
                client.get_access_token()


class TestMPesaTransactionHandler:
    """Test M-Pesa transaction handling"""
    
    def test_transaction_validation(self, sample_mpesa_transaction):
        """Test transaction data validation"""
        handler = MPesaTransactionHandler()
        is_valid = handler.validate_transaction(sample_mpesa_transaction)
        assert is_valid is True
    
    def test_invalid_transaction_amount(self, sample_mpesa_transaction):
        """Test validation with invalid amount"""
        sample_mpesa_transaction['TransAmount'] = '-100'
        handler = MPesaTransactionHandler()
        is_valid = handler.validate_transaction(sample_mpesa_transaction)
        assert is_valid is False
    
    def test_invalid_phone_number(self, sample_mpesa_transaction):
        """Test validation with invalid phone number"""
        sample_mpesa_transaction['MSISDN'] = '123'  # Too short
        handler = MPesaTransactionHandler()
        is_valid = handler.validate_transaction(sample_mpesa_transaction)
        assert is_valid is False
    
    def test_transaction_enrichment(self, sample_mpesa_transaction):
        """Test transaction data enrichment"""
        handler = MPesaTransactionHandler()
        enriched = handler.enrich_transaction(sample_mpesa_transaction)
        
        assert 'timestamp' in enriched
        assert 'customer_name' in enriched
        assert enriched['customer_name'] == 'John Doe Smith'
    
    def test_duplicate_transaction_detection(self, sample_mpesa_transaction):
        """Test duplicate transaction detection"""
        handler = MPesaTransactionHandler()
        
        # First transaction should not be duplicate
        is_duplicate = handler.is_duplicate(sample_mpesa_transaction['TransID'])
        assert is_duplicate is False
        
        # Mark as processed
        handler.mark_processed(sample_mpesa_transaction['TransID'])
        
        # Second attempt should be duplicate
        is_duplicate = handler.is_duplicate(sample_mpesa_transaction['TransID'])
        assert is_duplicate is True


class TestC2BWebhookValidation:
    """Test C2B webhook validation"""
    
    def test_valid_c2b_payload(self, sample_mpesa_transaction):
        """Test validation of valid C2B payload"""
        from ingestion.webhook_receiver import validate_c2b_payload
        
        is_valid = validate_c2b_payload(sample_mpesa_transaction)
        assert is_valid is True
    
    def test_missing_required_fields(self, sample_mpesa_transaction):
        """Test validation with missing required fields"""
        from ingestion.webhook_receiver import validate_c2b_payload
        
        del sample_mpesa_transaction['TransID']
        is_valid = validate_c2b_payload(sample_mpesa_transaction)
        assert is_valid is False
    
    def test_malformed_timestamp(self, sample_mpesa_transaction):
        """Test validation with malformed timestamp"""
        from ingestion.webhook_receiver import validate_c2b_payload
        
        sample_mpesa_transaction['TransTime'] = 'invalid_timestamp'
        is_valid = validate_c2b_payload(sample_mpesa_transaction)
        assert is_valid is False


@pytest.mark.integration
class TestDarajaIntegrationFlow:
    """Integration tests for complete Daraja flow"""
    
    @pytest.mark.skip(reason="Requires live Daraja API credentials")
    def test_end_to_end_c2b_flow(self, mock_env_vars):
        """Test complete C2B transaction flow"""
        # This would test the full flow with actual API calls
        # Skip by default to avoid hitting live API in CI/CD
        pass
    
    @pytest.mark.skip(reason="Requires live Daraja API credentials")
    def test_end_to_end_stk_push_flow(self, mock_env_vars):
        """Test complete STK Push flow"""
        # This would test the full STK Push flow
        # Skip by default to avoid hitting live API in CI/CD
        pass
