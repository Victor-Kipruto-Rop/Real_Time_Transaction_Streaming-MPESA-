"""
AWS RDS IAM Authentication Connection Module

This module provides secure connection to AWS RDS using IAM authentication.
Credentials are loaded from environment variables, not hardcoded.

Usage:
    from ingestion.rds_connection import connect_to_rds, test_connection

    conn = connect_to_rds()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('SELECT * FROM transactions LIMIT 5')
            for row in cur.fetchall():
                print(row)
            cur.close()
        finally:
            conn.close()
"""

import os
import sys
import logging
import psycopg2
import boto3
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def load_environment_variables() -> Tuple[str, int, str, str, str, str]:
    """
    Load RDS connection parameters from environment variables.

    Returns:
        Tuple of (host, port, database, user, region, db_name)

    Raises:
        KeyError: If required environment variables are missing
    """
    required_vars = [
        'RDS_DB_HOST',
        'RDS_DB_PORT',
        'RDS_DB_NAME',
        'RDS_DB_USER',
        'AWS_REGION'
    ]

    missing = [var for var in required_vars if var not in os.environ]
    if missing:
        raise KeyError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Please ensure .env file is loaded or variables are set."
        )

    host = os.environ['RDS_DB_HOST']
    port = int(os.environ['RDS_DB_PORT'])
    database = os.environ['RDS_DB_NAME']
    user = os.environ['RDS_DB_USER']
    region = os.environ['AWS_REGION']

    return host, port, database, user, region, database


def generate_iam_auth_token(host: str, port: int, user: str, region: str) -> str:
    """
    Generate a temporary IAM authentication token for RDS.

    Args:
        host: RDS instance hostname
        port: RDS instance port
        user: Database username
        region: AWS region

    Returns:
        IAM authentication token (valid for 15 minutes)

    Raises:
        Exception: If token generation fails
    """
    try:
        client = boto3.client('rds', region_name=region)
        token = client.generate_db_auth_token(
            DBHostname=host,
            Port=port,
            DBUsername=user,
            Region=region
        )
        logger.debug(f"Generated IAM token for {user}@{host}:{port}")
        return token
    except Exception as e:
        logger.error(f"Error generating IAM token: {e}")
        raise


def connect_to_rds() -> Optional[psycopg2.extensions.connection]:
    """
    Establish a connection to AWS RDS using IAM authentication.

    Returns:
        psycopg2 connection object or None if connection fails

    Example:
        conn = connect_to_rds()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute('SELECT version();')
                print(cur.fetchone()[0])
                cur.close()
            finally:
                conn.close()
    """
    conn = None
    try:
        # Load environment variables
        host, port, database, user, region, db_name = load_environment_variables()

        logger.info(f"Generating IAM token for {user}@{host}:{port}...")
        auth_token = generate_iam_auth_token(host, port, user, region)

        logger.info(f"Connecting to RDS instance {database}...")
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=auth_token,
            sslmode='require'
        )
        conn.autocommit = True
        logger.info("✓ Connected successfully to RDS")
        return conn

    except KeyError as e:
        logger.error(f"Configuration Error: {e}")
        return None
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None


def test_connection() -> bool:
    """
    Test RDS connection by executing a simple query.

    Returns:
        True if successful, False otherwise
    """
    conn = None
    try:
        conn = connect_to_rds()
        if not conn:
            return False

        cur = conn.cursor()
        cur.execute('SELECT version();')
        version = cur.fetchone()[0]
        logger.info(f"✓ Database version: {version}")
        cur.close()
        return True

    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Load environment variables from .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        logger.warning("python-dotenv not installed. Ensure env vars are set.")

    logger.info("Testing AWS RDS IAM Authentication Connection...\n")
    success = test_connection()
    sys.exit(0 if success else 1)
