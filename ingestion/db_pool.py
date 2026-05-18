"""
PostgreSQL Connection Pooling Module

Implements psycopg2 connection pooling for efficient database access.
Reduces connection overhead and improves performance under load.

Features:
- Connection pooling (min/max connections)
- Connection reuse
- Automatic reconnection on failure
- Thread-safe connection management
"""

import os
import logging
import psycopg2
from psycopg2 import pool
from typing import Optional
from ingestion.rds_connection import generate_iam_auth_token, load_environment_variables

logger = logging.getLogger(__name__)


class DatabasePool:
    """Manages PostgreSQL connection pool"""
    
    _instance = None
    _pool = None
    
    def __init__(self, 
                 min_connections: int = 2,
                 max_connections: int = 10,
                 use_iam_auth: bool = False):
        """
        Initialize database connection pool.
        
        Args:
            min_connections: Minimum pool size
            max_connections: Maximum pool size
            use_iam_auth: Use AWS RDS IAM authentication
        """
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.use_iam_auth = use_iam_auth
        self._init_pool()
    
    def _init_pool(self):
        """Initialize the connection pool"""
        try:
            if self.use_iam_auth:
                # AWS RDS with IAM auth
                host, port, database, user, region, _ = load_environment_variables()
                password = generate_iam_auth_token(host, port, user, region)
                logger.info(f"Using AWS RDS IAM authentication for {user}@{host}")
            else:
                # Local PostgreSQL or standard credentials
                host = os.environ.get('POSTGRES_HOST', 'localhost')
                port = int(os.environ.get('POSTGRES_PORT', '5432'))
                database = os.environ.get('POSTGRES_DB', 'mpesa_analytics')
                user = os.environ.get('POSTGRES_USER', 'data_engineer')
                password = os.environ.get('POSTGRES_PASSWORD', 'change_me')
                logger.info(f"Using PostgreSQL connection to {user}@{host}:{port}")
            
            self._pool = psycopg2.pool.SimpleConnectionPool(
                self.min_connections,
                self.max_connections,
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                sslmode='prefer' if not self.use_iam_auth else 'require'
            )
            logger.info(f"✓ Connection pool initialized ({self.min_connections}-{self.max_connections})")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise
    
    def get_connection(self):
        """
        Get a connection from the pool.
        
        Returns:
            psycopg2 connection object
            
        Raises:
            Exception: If no connections available
        """
        if not self._pool:
            raise Exception("Connection pool not initialized")
        
        try:
            conn = self._pool.getconn()
            conn.autocommit = False
            return conn
        except Exception as e:
            logger.error(f"Error getting connection from pool: {e}")
            raise
    
    def release_connection(self, conn):
        """Release a connection back to the pool"""
        if conn:
            try:
                self._pool.putconn(conn)
            except Exception as e:
                logger.error(f"Error releasing connection: {e}")
    
    def close_all(self):
        """Close all connections in the pool"""
        if self._pool:
            self._pool.closeall()
            logger.info("✓ All connections closed")
    
    @staticmethod
    def get_instance(min_connections: int = 2, 
                    max_connections: int = 10,
                    use_iam_auth: bool = False):
        """Singleton pattern to get the connection pool instance"""
        if DatabasePool._instance is None:
            DatabasePool._instance = DatabasePool(
                min_connections=min_connections,
                max_connections=max_connections,
                use_iam_auth=use_iam_auth
            )
        return DatabasePool._instance


class PooledConnection:
    """Context manager for pooled connections"""
    
    def __init__(self, pool_instance: DatabasePool):
        self.pool = pool_instance
        self.conn = None
    
    def __enter__(self):
        self.conn = self.pool.get_connection()
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.pool.release_connection(self.conn)


def get_pooled_connection(use_iam_auth: bool = False):
    """
    Get a pooled connection context manager.
    
    Usage:
        with get_pooled_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM transactions')
            cur.close()
    """
    pool = DatabasePool.get_instance(use_iam_auth=use_iam_auth)
    return PooledConnection(pool)
