"""
Tests for AWS RDS IAM authentication
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from ingestion.rds_connection import RDSConnection, get_rds_connection


class TestRDSConnection:
    """Test RDS IAM authentication connection"""

    def test_iam_token_generation(self, mock_env_vars, mock_rds_iam_token):
        """Test IAM token generation for RDS"""
        with patch("boto3.client") as mock_boto_client:
            mock_rds_client = MagicMock()
            mock_rds_client.generate_db_auth_token.return_value = mock_rds_iam_token
            mock_boto_client.return_value = mock_rds_client

            rds_conn = RDSConnection(
                host="test-rds.amazonaws.com",
                port=5432,
                user="test_user",
                database="mpesa_test",
                region="us-east-1",
            )

            token = rds_conn.generate_auth_token()
            assert token == mock_rds_iam_token
            mock_rds_client.generate_db_auth_token.assert_called_once()

    def test_connection_with_iam_auth(self, mock_env_vars, mock_rds_iam_token):
        """Test database connection with IAM authentication"""
        with patch("boto3.client") as mock_boto_client, patch(
            "psycopg2.connect"
        ) as mock_pg_connect:
            mock_rds_client = MagicMock()
            mock_rds_client.generate_db_auth_token.return_value = mock_rds_iam_token
            mock_boto_client.return_value = mock_rds_client

            mock_connection = MagicMock()
            mock_pg_connect.return_value = mock_connection

            rds_conn = RDSConnection(
                host="test-rds.amazonaws.com",
                port=5432,
                user="test_user",
                database="mpesa_test",
                region="us-east-1",
            )

            conn = rds_conn.connect()
            assert conn is not None
            mock_pg_connect.assert_called_once()

    def test_connection_retry_logic(self, mock_env_vars):
        """Test connection retry on failure"""
        with patch("boto3.client") as mock_boto_client, patch(
            "psycopg2.connect"
        ) as mock_pg_connect:
            mock_rds_client = MagicMock()
            mock_rds_client.generate_db_auth_token.return_value = "token"
            mock_boto_client.return_value = mock_rds_client

            # First two attempts fail, third succeeds
            mock_pg_connect.side_effect = [
                Exception("Connection failed"),
                Exception("Connection failed"),
                MagicMock(),
            ]

            rds_conn = RDSConnection(
                host="test-rds.amazonaws.com",
                port=5432,
                user="test_user",
                database="mpesa_test",
                region="us-east-1",
                max_retries=3,
            )

            conn = rds_conn.connect()
            assert conn is not None
            assert mock_pg_connect.call_count == 3

    def test_connection_failure_after_max_retries(self, mock_env_vars):
        """Test connection failure after exhausting retries"""
        with patch("boto3.client") as mock_boto_client, patch(
            "psycopg2.connect"
        ) as mock_pg_connect:
            mock_rds_client = MagicMock()
            mock_rds_client.generate_db_auth_token.return_value = "token"
            mock_boto_client.return_value = mock_rds_client

            mock_pg_connect.side_effect = Exception("Connection failed")

            rds_conn = RDSConnection(
                host="test-rds.amazonaws.com",
                port=5432,
                user="test_user",
                database="mpesa_test",
                region="us-east-1",
                max_retries=2,
            )

            with pytest.raises(Exception):
                rds_conn.connect()

    def test_ssl_configuration(self, mock_env_vars, mock_rds_iam_token):
        """Test SSL configuration for RDS connection"""
        with patch("boto3.client") as mock_boto_client, patch(
            "psycopg2.connect"
        ) as mock_pg_connect:
            mock_rds_client = MagicMock()
            mock_rds_client.generate_db_auth_token.return_value = mock_rds_iam_token
            mock_boto_client.return_value = mock_rds_client

            mock_connection = MagicMock()
            mock_pg_connect.return_value = mock_connection

            rds_conn = RDSConnection(
                host="test-rds.amazonaws.com",
                port=5432,
                user="test_user",
                database="mpesa_test",
                region="us-east-1",
                ssl_mode="require",
            )

            conn = rds_conn.connect()

            # Verify SSL was configured in connection call
            call_kwargs = mock_pg_connect.call_args[1]
            assert "sslmode" in call_kwargs
            assert call_kwargs["sslmode"] == "require"

    def test_connection_pool_integration(self, mock_env_vars):
        """Test RDS connection with connection pooling"""
        with patch("boto3.client") as mock_boto_client, patch(
            "psycopg2.pool.SimpleConnectionPool"
        ) as mock_pool:
            mock_rds_client = MagicMock()
            mock_rds_client.generate_db_auth_token.return_value = "token"
            mock_boto_client.return_value = mock_rds_client

            mock_pool_instance = MagicMock()
            mock_pool.return_value = mock_pool_instance

            rds_conn = RDSConnection(
                host="test-rds.amazonaws.com",
                port=5432,
                user="test_user",
                database="mpesa_test",
                region="us-east-1",
                use_pool=True,
                pool_size=10,
            )

            pool = rds_conn.get_connection_pool()
            assert pool is not None
            mock_pool.assert_called_once()

    def test_token_refresh_on_expiry(self, mock_env_vars):
        """Test automatic token refresh when expired"""
        with patch("boto3.client") as mock_boto_client, patch(
            "psycopg2.connect"
        ) as mock_pg_connect:
            mock_rds_client = MagicMock()
            # Return different tokens on successive calls
            mock_rds_client.generate_db_auth_token.side_effect = ["token1", "token2"]
            mock_boto_client.return_value = mock_rds_client

            mock_connection = MagicMock()
            mock_pg_connect.return_value = mock_connection

            rds_conn = RDSConnection(
                host="test-rds.amazonaws.com",
                port=5432,
                user="test_user",
                database="mpesa_test",
                region="us-east-1",
            )

            # First connection
            conn1 = rds_conn.connect()

            # Simulate token expiry and reconnect
            rds_conn._token_expired = True
            conn2 = rds_conn.connect()

            # Should have generated token twice
            assert mock_rds_client.generate_db_auth_token.call_count == 2


class TestRDSConnectionFactory:
    """Test RDS connection factory function"""

    def test_get_rds_connection_from_env(self, mock_env_vars):
        """Test creating RDS connection from environment variables"""
        with patch("boto3.client"), patch("psycopg2.connect"):
            conn = get_rds_connection()
            assert conn is not None

    def test_get_rds_connection_with_custom_params(self, mock_env_vars):
        """Test creating RDS connection with custom parameters"""
        with patch("boto3.client"), patch("psycopg2.connect"):
            conn = get_rds_connection(
                host="custom-host.amazonaws.com", port=5433, database="custom_db"
            )
            assert conn is not None


@pytest.mark.integration
class TestRDSIntegration:
    """Integration tests for RDS connection"""

    @pytest.mark.skip(reason="Requires AWS credentials and RDS instance")
    def test_real_rds_connection(self):
        """Test actual RDS connection with real credentials"""
        # This would test with actual AWS RDS instance
        # Skip by default to avoid AWS costs in CI/CD
        pass

    @pytest.mark.skip(reason="Requires AWS credentials and RDS instance")
    def test_rds_query_execution(self):
        """Test executing queries on RDS"""
        # This would test actual query execution
        # Skip by default to avoid AWS costs in CI/CD
        pass
