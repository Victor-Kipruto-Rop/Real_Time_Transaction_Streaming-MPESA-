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
import time
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
    host = os.getenv("RDS_DB_HOST") or os.getenv("POSTGRES_HOST")
    port = os.getenv("RDS_DB_PORT") or os.getenv("POSTGRES_PORT")
    database = os.getenv("RDS_DB_NAME") or os.getenv("POSTGRES_DB")
    user = os.getenv("RDS_DB_USER") or os.getenv("POSTGRES_USER")
    region = os.getenv("AWS_REGION", "us-east-1")

    missing = []
    if not host:
        missing.append("RDS_DB_HOST/POSTGRES_HOST")
    if not port:
        missing.append("RDS_DB_PORT/POSTGRES_PORT")
    if not database:
        missing.append("RDS_DB_NAME/POSTGRES_DB")
    if not user:
        missing.append("RDS_DB_USER/POSTGRES_USER")

    if missing:
        raise KeyError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Please ensure .env file is loaded or variables are set."
        )

    return host, int(port), database, user, region, database


class RDSConnection:
    """Backward-compatible RDS IAM-auth connection helper."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        database: str,
        region: str,
        ssl_mode: str = "require",
        max_retries: int = 1,
        use_pool: bool = False,
        pool_size: int = 5,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.database = database
        self.region = region
        self.ssl_mode = ssl_mode
        self.max_retries = max(1, max_retries)
        self.use_pool = use_pool
        self.pool_size = pool_size
        self._cached_token: Optional[str] = None
        self._token_expired = True
        self._pool = None

    def generate_auth_token(self) -> str:
        token = generate_iam_auth_token(self.host, self.port, self.user, self.region)
        self._cached_token = token
        self._token_expired = False
        return token

    def _get_token(self) -> str:
        if self._cached_token is None or self._token_expired:
            return self.generate_auth_token()
        return self._cached_token

    def connect(self):
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                token = self._get_token()
                return psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.user,
                    password=token,
                    sslmode=self.ssl_mode,
                )
            except Exception as exc:
                last_error = exc
                self._token_expired = True
                if attempt < self.max_retries:
                    time.sleep(0.1)
        raise last_error

    def get_connection_pool(self):
        if self._pool is None:
            if not self.use_pool:
                return None
            token = self._get_token()
            self._pool = psycopg2.pool.SimpleConnectionPool(
                1,
                self.pool_size,
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=token,
                sslmode=self.ssl_mode,
            )
        return self._pool


def get_rds_connection(
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: Optional[str] = None,
    user: Optional[str] = None,
    region: Optional[str] = None,
):
    """Create and return a connection using args or environment defaults."""
    env_host, env_port, env_database, env_user, env_region, _ = load_environment_variables()
    rds_connection = RDSConnection(
        host=host or env_host,
        port=port or env_port,
        user=user or env_user,
        database=database or env_database,
        region=region or env_region,
    )
    return rds_connection.connect()


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
        client = boto3.client("rds", region_name=region)
        token = client.generate_db_auth_token(
            DBHostname=host, Port=port, DBUsername=user, Region=region
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
            sslmode="require",
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
        cur.execute("SELECT version();")
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


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
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
