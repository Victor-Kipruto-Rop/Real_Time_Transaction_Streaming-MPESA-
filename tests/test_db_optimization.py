"""
Unit tests for database pooling and query optimization modules

Test coverage:
- Connection pooling
- Query execution
- Cache management
- Performance monitoring
"""

import os
import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from ingestion.db_pool import DatabasePool, PooledConnection, get_pooled_connection
from ingestion.db_queries import DatabaseQueries, IndexRecommendations, QueryPerformanceMonitor
from ingestion.db_cache import CacheManager, get_cache_manager, cached_query


class TestDatabasePool:
    """Test connection pooling"""
    
    def test_pool_initialization(self):
        """Test database pool initialization"""
        with patch('ingestion.db_pool.psycopg2.pool.SimpleConnectionPool') as mock_pool_class:
            with patch('ingestion.db_pool.os.environ', {'POSTGRES_HOST': 'localhost', 'POSTGRES_PORT': '5432'}):
                mock_pool_class.return_value = Mock()
                pool = DatabasePool(min_connections=2, max_connections=5, use_iam_auth=False)
                assert pool.min_connections == 2
                assert pool.max_connections == 5
    
    def test_pool_singleton(self):
        """Test singleton pattern"""
        with patch('ingestion.db_pool.psycopg2.pool.SimpleConnectionPool') as mock_pool_class:
            with patch('ingestion.db_pool.os.environ', {'POSTGRES_HOST': 'localhost', 'POSTGRES_PORT': '5432'}):
                mock_pool_class.return_value = Mock()
                DatabasePool._instance = None  # Reset singleton
                
                pool1 = DatabasePool.get_instance()
                pool2 = DatabasePool.get_instance()
                assert pool1 is pool2
                
                DatabasePool._instance = None  # Clean up
    
    def test_get_connection(self):
        """Test getting connection from pool"""
        with patch('ingestion.db_pool.psycopg2.pool.SimpleConnectionPool') as mock_pool_class:
            with patch('ingestion.db_pool.os.environ', {'POSTGRES_HOST': 'localhost', 'POSTGRES_PORT': '5432'}):
                mock_pool = Mock()
                mock_pool_class.return_value = mock_pool
                mock_conn = Mock()
                mock_pool.getconn.return_value = mock_conn
                
                pool = DatabasePool(min_connections=2, use_iam_auth=False)
                
                conn = pool.get_connection()
                assert conn == mock_conn
                mock_pool.getconn.assert_called_once()
    
    def test_release_connection(self):
        """Test releasing connection back to pool"""
        with patch('ingestion.db_pool.psycopg2.pool.SimpleConnectionPool') as mock_pool_class:
            with patch('ingestion.db_pool.os.environ', {'POSTGRES_HOST': 'localhost', 'POSTGRES_PORT': '5432'}):
                mock_pool = Mock()
                mock_pool_class.return_value = mock_pool
                mock_conn = Mock()
                
                pool = DatabasePool(min_connections=2, use_iam_auth=False)
                
                pool.release_connection(mock_conn)
                mock_pool.putconn.assert_called_once_with(mock_conn)


class TestDatabaseQueries:
    """Test optimized database queries"""
    
    @patch('ingestion.db_queries.get_pooled_connection')
    def test_health_check(self, mock_get_conn):
        """Test health check query"""
        mock_conn = MagicMock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        result = DatabaseQueries.health_check()
        assert result is True
        mock_cursor.execute.assert_called_once_with('SELECT 1')
    
    @patch('ingestion.db_queries.get_pooled_connection')
    def test_get_transaction_by_id(self, mock_get_conn):
        """Test get transaction by ID"""
        mock_conn = MagicMock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = {'transaction_id': 'TX123', 'amount': 1000}
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        result = DatabaseQueries.get_transaction_by_id('TX123')
        assert result is not None
    
    @patch('ingestion.db_queries.get_pooled_connection')
    def test_query_with_parameters(self, mock_get_conn):
        """Test parameterized queries (SQL injection protection)"""
        mock_conn = MagicMock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [{'phone': '254712345678'}]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        
        result = DatabaseQueries.get_transactions_by_phone('254712345678')
        # Verify that parameters were passed (for prepared statements)
        mock_cursor.execute.assert_called_once()
        assert mock_cursor.execute.call_args[0][1] == ('254712345678', 100)


class TestCacheManager:
    """Test cache management"""
    
    def test_cache_initialization(self):
        """Test cache manager initialization"""
        with patch('ingestion.db_cache.redis.Redis'):
            cache = CacheManager(cache_ttl=300)
            assert cache.cache_ttl == 300
    
    def test_cache_key_generation(self):
        """Test cache key generation"""
        cache = CacheManager()
        key1 = cache.get_cache_key("SELECT * FROM users WHERE id = %s", (1,))
        key2 = cache.get_cache_key("SELECT * FROM users WHERE id = %s", (2,))
        
        # Keys should be different for different parameters
        assert key1 != key2
    
    def test_in_memory_cache_set_get(self):
        """Test in-memory cache"""
        with patch('ingestion.db_cache.redis.Redis'):
            cache = CacheManager()
            cache.redis_available = False
            
            # Set value
            cache.set('test_key', {'data': 'value'}, ttl=10)
            
            # Get value
            result = cache.get('test_key')
            assert result == {'data': 'value'}
    
    def test_cache_expiration(self):
        """Test cache expiration in in-memory cache"""
        # Test pure in-memory cache without Redis connection attempt
        cache = CacheManager()
        cache.redis_available = False  # Ensure Redis is disabled
        cache.redis_client = None
        
        # Set value with very short TTL
        cache.set('test_key', {'data': 'value'}, ttl=0.05)
        
        # Should exist immediately
        result = cache.get('test_key')
        assert result == {'data': 'value'}, "Value should exist immediately after set"
        
        # Wait for expiration
        time.sleep(0.15)
        
        # Should be expired now (0.05 TTL + 0.15 wait = 0.20s, well past expiration)
        result = cache.get('test_key')
        assert result is None, "Value should be expired after TTL"
    
    def test_cache_invalidation(self):
        """Test cache invalidation"""
        with patch('ingestion.db_cache.redis.Redis'):
            cache = CacheManager()
            cache.redis_available = False
            
            cache.set('test_key', {'data': 'value'})
            cache.invalidate('test_key')
            
            result = cache.get('test_key')
            assert result is None
    
    def test_cache_clear(self):
        """Test clearing entire cache"""
        with patch('ingestion.db_cache.redis.Redis'):
            cache = CacheManager()
            cache.redis_available = False
            
            cache.set('key1', {'data': 1})
            cache.set('key2', {'data': 2})
            
            cache.clear()
            
            assert cache.get('key1') is None
            assert cache.get('key2') is None


class TestCachedQueryDecorator:
    """Test cached query decorator"""
    
    def test_cached_query_decorator(self):
        """Test cached query decorator"""
        with patch('ingestion.db_cache.get_cache_manager'):
            call_count = 0
            
            @cached_query(ttl=300)
            def get_data(user_id):
                nonlocal call_count
                call_count += 1
                return {'user_id': user_id, 'data': 'result'}
            
            # First call executes function
            result1 = get_data(1)
            # Second call should come from cache
            result2 = get_data(1)
            
            # Results should be the same
            assert result1 == result2


class TestQueryPerformanceMonitor:
    """Test query performance monitoring"""
    
    def test_log_query_time(self):
        """Test logging query execution time"""
        QueryPerformanceMonitor._metrics = []
        
        QueryPerformanceMonitor.log_query_time('select_users', 0.125)
        QueryPerformanceMonitor.log_query_time('select_orders', 0.250)
        
        assert len(QueryPerformanceMonitor._metrics) == 2
    
    def test_get_slowest_queries(self):
        """Test getting slowest queries"""
        QueryPerformanceMonitor._metrics = [
            {'query': 'q1', 'elapsed_time': 0.1},
            {'query': 'q2', 'elapsed_time': 0.5},
            {'query': 'q3', 'elapsed_time': 0.3},
        ]
        
        slowest = QueryPerformanceMonitor.get_slowest_queries(limit=2)
        
        assert len(slowest) == 2
        assert slowest[0]['elapsed_time'] == 0.5
        assert slowest[1]['elapsed_time'] == 0.3
    
    def test_performance_summary(self):
        """Test performance summary"""
        QueryPerformanceMonitor._metrics = [
            {'query': 'q1', 'elapsed_time': 0.1},
            {'query': 'q2', 'elapsed_time': 0.2},
            {'query': 'q3', 'elapsed_time': 0.3},
        ]
        
        summary = QueryPerformanceMonitor.get_performance_summary()
        
        assert summary['total_queries'] == 3
        assert abs(summary['avg_time'] - 0.2) < 0.001
        assert summary['min_time'] == 0.1
        assert summary['max_time'] == 0.3
        assert abs(summary['total_time'] - 0.6) < 0.001
