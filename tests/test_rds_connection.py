"""
Unit tests for AWS RDS IAM authentication connection module

Test coverage:
- Environment variable loading
- Token generation
- Connection establishment
- Connection testing
"""

import os
import pytest
import psycopg2
from unittest.mock import Mock, patch, MagicMock
from ingestion.rds_connection import (
    load_environment_variables,
    generate_iam_auth_token,
    connect_to_rds,
    test_connection
)


class TestLoadEnvironmentVariables:
    """Test environment variable loading"""

    def test_load_all_variables_success(self):
        """Test successful loading of all required environment variables"""
        with patch.dict(os.environ, {
            'RDS_DB_HOST': 'test-db.region.rds.amazonaws.com',
            'RDS_DB_PORT': '5432',
            'RDS_DB_NAME': 'testdb',
            'RDS_DB_USER': 'postgres',
            'AWS_REGION': 'us-west-1'
        }):
            host, port, database, user, region, db_name = load_environment_variables()
            assert host == 'test-db.region.rds.amazonaws.com'
            assert port == 5432
            assert database == 'testdb'
            assert user == 'postgres'
            assert region == 'us-west-1'
            assert db_name == 'testdb'

    def test_missing_rds_host(self):
        """Test error when RDS_DB_HOST is missing"""
        with patch.dict(os.environ, {
            'RDS_DB_PORT': '5432',
            'RDS_DB_NAME': 'testdb',
            'RDS_DB_USER': 'postgres',
            'AWS_REGION': 'us-west-1'
        }, clear=True):
            with pytest.raises(KeyError):
                load_environment_variables()

    def test_missing_multiple_variables(self):
        """Test error when multiple required variables are missing"""
        with patch.dict(os.environ, {
            'RDS_DB_HOST': 'test-db.region.rds.amazonaws.com'
        }, clear=True):
            with pytest.raises(KeyError) as exc_info:
                load_environment_variables()
            error_msg = str(exc_info.value)
            assert 'RDS_DB_PORT' in error_msg
            assert 'RDS_DB_NAME' in error_msg

    def test_port_conversion_to_int(self):
        """Test that port is correctly converted to integer"""
        with patch.dict(os.environ, {
            'RDS_DB_HOST': 'test-db.region.rds.amazonaws.com',
            'RDS_DB_PORT': '5432',
            'RDS_DB_NAME': 'testdb',
            'RDS_DB_USER': 'postgres',
            'AWS_REGION': 'us-west-1'
        }):
            _, port, _, _, _, _ = load_environment_variables()
            assert isinstance(port, int)
            assert port == 5432


class TestGenerateIAMAuthToken:
    """Test IAM token generation"""

    @patch('ingestion.rds_connection.boto3.client')
    def test_token_generation_success(self, mock_boto3_client):
        """Test successful token generation"""
        mock_rds_client = Mock()
        mock_boto3_client.return_value = mock_rds_client
        mock_rds_client.generate_db_auth_token.return_value = 'mock-token-12345'

        token = generate_iam_auth_token(
            host='test-db.region.rds.amazonaws.com',
            port=5432,
            user='postgres',
            region='us-west-1'
        )

        assert token == 'mock-token-12345'
        mock_boto3_client.assert_called_once_with('rds', region_name='us-west-1')
        mock_rds_client.generate_db_auth_token.assert_called_once_with(
            DBHostname='test-db.region.rds.amazonaws.com',
            Port=5432,
            DBUsername='postgres',
            Region='us-west-1'
        )

    @patch('ingestion.rds_connection.boto3.client')
    def test_token_generation_failure(self, mock_boto3_client):
        """Test token generation failure handling"""
        mock_boto3_client.side_effect = Exception('AWS credentials not found')

        with pytest.raises(Exception) as exc_info:
            generate_iam_auth_token(
                host='test-db.region.rds.amazonaws.com',
                port=5432,
                user='postgres',
                region='us-west-1'
            )
        assert 'AWS credentials not found' in str(exc_info.value)


class TestConnectToRDS:
    """Test RDS connection"""

    @patch('ingestion.rds_connection.generate_iam_auth_token')
    @patch('ingestion.rds_connection.psycopg2.connect')
    @patch.dict(os.environ, {
        'RDS_DB_HOST': 'test-db.region.rds.amazonaws.com',
        'RDS_DB_PORT': '5432',
        'RDS_DB_NAME': 'testdb',
        'RDS_DB_USER': 'postgres',
        'AWS_REGION': 'us-west-1'
    })
    def test_connection_success(self, mock_psycopg2_connect, mock_generate_token):
        """Test successful database connection"""
        mock_generate_token.return_value = 'mock-token'
        mock_conn = Mock()
        mock_psycopg2_connect.return_value = mock_conn

        result = connect_to_rds()

        assert result == mock_conn
        mock_psycopg2_connect.assert_called_once_with(
            host='test-db.region.rds.amazonaws.com',
            port=5432,
            database='testdb',
            user='postgres',
            password='mock-token',
            sslmode='require'
        )
        mock_conn.autocommit = True

    @patch.dict(os.environ, {}, clear=True)
    def test_connection_missing_env_vars(self):
        """Test connection failure when env vars are missing"""
        result = connect_to_rds()
        assert result is None

    @patch('ingestion.rds_connection.generate_iam_auth_token')
    @patch('ingestion.rds_connection.psycopg2.connect')
    @patch.dict(os.environ, {
        'RDS_DB_HOST': 'test-db.region.rds.amazonaws.com',
        'RDS_DB_PORT': '5432',
        'RDS_DB_NAME': 'testdb',
        'RDS_DB_USER': 'postgres',
        'AWS_REGION': 'us-west-1'
    })
    def test_connection_failure(self, mock_psycopg2_connect, mock_generate_token):
        """Test connection failure handling"""
        mock_generate_token.return_value = 'mock-token'
        mock_psycopg2_connect.side_effect = psycopg2.OperationalError('Connection refused')

        result = connect_to_rds()
        assert result is None


class TestTestConnection:
    """Test connection validation"""

    @patch('ingestion.rds_connection.connect_to_rds')
    def test_connection_test_success(self, mock_connect):
        """Test successful connection test"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ('PostgreSQL 13.0',)

        result = test_connection()

        assert result is True
        mock_cursor.execute.assert_called_once_with('SELECT version();')
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('ingestion.rds_connection.connect_to_rds')
    def test_connection_test_failure_no_connection(self, mock_connect):
        """Test connection test failure when connect_to_rds returns None"""
        mock_connect.return_value = None

        result = test_connection()
        assert result is False

    @patch('ingestion.rds_connection.connect_to_rds')
    def test_connection_test_query_failure(self, mock_connect):
        """Test connection test failure when query fails"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = psycopg2.ProgrammingError('Query error')

        result = test_connection()

        assert result is False
        mock_conn.close.assert_called_once()
