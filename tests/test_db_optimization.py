"""
Tests for database optimization features
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from ingestion.db_pool import DatabasePool
from ingestion.db_queries import DatabaseQueries, IndexRecommendations
from ingestion.db_cache import QueryCache


class TestDatabasePool:
    """Test database connection pooling"""
    
    def test_pool_initialization(self, mock_env_vars):
        """Test connection pool initialization"""
        with patch('psycopg2.pool.SimpleConnectionPool') as mock_pool:
            mock_pool_instance = MagicMock()
            mock_pool.return_value = mock_pool_instance
            
            pool = DatabasePool(
                minconn=1,
                maxconn=10,
                host='localhost',
                port=5432,
                database='mpesa_test',
                user='test_user',
                password='test_password'
            )
            
            assert pool is not None
            mock_pool.assert_called_once()
    
    def test_get_connection_from_pool(self, mock_env_vars):
        """Test getting connection from pool"""
        with patch('psycopg2.pool.SimpleConnectionPool') as mock_pool:
            mock_pool_instance = MagicMock()
            mock_connection = MagicMock()
            mock_pool_instance.getconn.return_value = mock_connection
            mock_pool.return_value = mock_pool_instance
            
            pool = DatabasePool(
                minconn=1,
                maxconn=10,
                host='localhost',
                port=5432,
                database='mpesa_test',
                user='test_user',
                password='test_password'
            )
            
            conn = pool.get_connection()
            assert conn == mock_connection
            mock_pool_instance.getconn.assert_called_once()
    
    def test_return_connection_to_pool(self, mock_env_vars):
        """Test returning connection to pool"""
        with patch('psycopg2.pool.SimpleConnectionPool') as mock_pool:
            mock_pool_instance = MagicMock()
            mock_connection = MagicMock()
            mock_pool.return_value = mock_pool_instance
            
            pool = DatabasePool(
                minconn=1,
                maxconn=10,
                host='localhost',
                port=5432,
                database='mpesa_test',
                user='test_user',
                password='test_password'
            )
            
            pool.return_connection(mock_connection)
            mock_pool_instance.putconn.assert_called_once_with(mock_connection)
    
    def test_pool_exhaustion_handling(self, mock_env_vars):
        """Test handling when pool is exhausted"""
        with patch('psycopg2.pool.SimpleConnectionPool') as mock_pool:
            mock_pool_instance = MagicMock()
            mock_pool_instance.getconn.side_effect = Exception('Pool exhausted')
            mock_pool.return_value = mock_pool_instance
            
            pool = DatabasePool(
                minconn=1,
                maxconn=2,
                host='localhost',
                port=5432,
                database='mpesa_test',
                user='test_user',
                password='test_password'
            )
            
            with pytest.raises(Exception):
                pool.get_connection()
    
    def test_pool_close(self, mock_env_vars):
        """Test closing connection pool"""
        with patch('psycopg2.pool.SimpleConnectionPool') as mock_pool:
            mock_pool_instance = MagicMock()
            mock_pool.return_value = mock_pool_instance
            
            pool = DatabasePool(
                minconn=1,
                maxconn=10,
                host='localhost',
                port=5432,
                database='mpesa_test',
                user='test_user',
                password='test_password'
            )
            
            pool.close()
            mock_pool_instance.closeall.assert_called_once()


class TestDatabaseQueries:
    """Test optimized database queries"""
    
    def test_bulk_insert_transactions(self, mock_postgres_connection):
        """Test bulk insert optimization"""
        transactions = [
            {'trans_id': 'TXN1', 'amount': 100, 'phone': '254712345678'},
            {'trans_id': 'TXN2', 'amount': 200, 'phone': '254712345679'},
            {'trans_id': 'TXN3', 'amount': 300, 'phone': '254712345680'}
        ]
        
        with patch('psycopg2.connect', return_value=mock_postgres_connection):
            db_queries = DatabaseQueries()
            result = db_queries.bulk_insert_transactions(transactions)
            
            assert result is True
            # Verify execute_batch or execute_values was used
            mock_postgres_connection.cursor().execute.assert_called()
    
    def test_optimized_transaction_query(self, mock_postgres_connection):
        """Test optimized transaction query with indexes"""
        with patch('psycopg2.connect', return_value=mock_postgres_connection):
            mock_cursor = mock_postgres_connection.cursor()
            mock_cursor.fetchall.return_value = [
                ('TXN1', 100, '254712345678'),
                ('TXN2', 200, '254712345679')
            ]
            
            db_queries = DatabaseQueries()
            results = db_queries.get_transactions_by_date_range(
                start_date='2026-06-01',
                end_date='2026-06-13'
            )
            
            assert len(results) == 2
            mock_cursor.execute.assert_called_once()
    
    def test_aggregation_query_optimization(self, mock_postgres_connection):
        """Test optimized aggregation queries"""
        with patch('psycopg2.connect', return_value=mock_postgres_connection):
            mock_cursor = mock_postgres_connection.cursor()
            mock_cursor.fetchone.return_value = (50000.00, 100)
            
            db_queries = DatabaseQueries()
            result = db_queries.get_daily_summary('2026-06-13')
            
            assert result['total_amount'] == 50000.00
            assert result['transaction_count'] == 100
    
    def test_query_with_prepared_statement(self, mock_postgres_connection):
        """Test using prepared statements for repeated queries"""
        with patch('psycopg2.connect', return_value=mock_postgres_connection):
            db_queries = DatabaseQueries()
            
            # Execute same query multiple times
            for i in range(5):
                db_queries.get_transaction_by_id(f'TXN{i}')
            
            # Should use prepared statement for efficiency
            assert mock_postgres_connection.cursor().execute.call_count == 5
    
    def test_health_check_query(self, mock_postgres_connection):
        """Test database health check"""
        with patch('psycopg2.connect', return_value=mock_postgres_connection):
            mock_cursor = mock_postgres_connection.cursor()
            mock_cursor.fetchone.return_value = (1,)
            
            is_healthy = DatabaseQueries.health_check()
            assert is_healthy is True


class TestIndexRecommendations:
    """Test index recommendation and creation"""
    
    def test_analyze_missing_indexes(self, mock_postgres_connection):
        """Test analyzing for missing indexes"""
        with patch('psycopg2.connect', return_value=mock_postgres_connection):
            mock_cursor = mock_postgres_connection.cursor()
            mock_cursor.fetchall.return_value = [
                ('mpesa_transactions_raw', 'phone_number', 1000),
                ('mpesa_transactions_raw', 'transaction_time', 800)
            ]
            
            recommendations = IndexRecommendations.analyze_missing_indexes()
            assert len(recommendations) > 0
    
    def test_create_recommended_indexes(self, mock_postgres_connection):
        """Test creating recommended indexes"""
        with patch('psycopg2.connect', return_value=mock_postgres_connection):
            IndexRecommendations.create_recommended_indexes()
            
            # Verify CREATE INDEX statements were executed
            mock_postgres_connection.cursor().execute.assert_called()
    
    def test_index_usage_statistics(self, mock_postgres_connection):
        """Test getting index usage statistics"""
        with patch('psycopg2.connect', return_value=mock_postgres_connection):
            mock_cursor = mock_postgres_connection.cursor()
            mock_cursor.fetchall.return_value = [
                ('idx_phone_number', 5000, 0.95),
                ('idx_transaction_time', 3000, 0.80)
            ]
            
            stats = IndexRecommendations.get_index_usage_stats()
            assert len(stats) == 2
            assert stats[0]['index_name'] == 'idx_phone_number'


class TestQueryCache:
    """Test query result caching"""
    
    def test_cache_query_result(self):
        """Test caching query results"""
        cache = QueryCache(ttl=300)
        
        query = "SELECT * FROM transactions WHERE id = %s"
        params = ('TXN123',)
        result = [{'id': 'TXN123', 'amount': 100}]
        
        cache.set(query, params, result)
        cached_result = cache.get(query, params)
        
        assert cached_result == result
    
    def test_cache_expiration(self):
        """Test cache expiration"""
        cache = QueryCache(ttl=1)  # 1 second TTL
        
        query = "SELECT * FROM transactions WHERE id = %s"
        params = ('TXN123',)
        result = [{'id': 'TXN123', 'amount': 100}]
        
        cache.set(query, params, result)
        
        # Immediately should be cached
        assert cache.get(query, params) == result
        
        # After expiration, should return None
        import time
        time.sleep(2)
        assert cache.get(query, params) is None
    
    def test_cache_invalidation(self):
        """Test cache invalidation"""
        cache = QueryCache(ttl=300)
        
        query = "SELECT * FROM transactions WHERE id = %s"
        params = ('TXN123',)
        result = [{'id': 'TXN123', 'amount': 100}]
        
        cache.set(query, params, result)
        assert cache.get(query, params) == result
        
        # Invalidate cache
        cache.invalidate(query, params)
        assert cache.get(query, params) is None
    
    def test_cache_clear_all(self):
        """Test clearing entire cache"""
        cache = QueryCache(ttl=300)
        
        # Add multiple entries
        cache.set("query1", ('param1',), [{'result': 1}])
        cache.set("query2", ('param2',), [{'result': 2}])
        
        # Clear all
        cache.clear()
        
        assert cache.get("query1", ('param1',)) is None
        assert cache.get("query2", ('param2',)) is None
    
    def test_cache_hit_rate_tracking(self):
        """Test tracking cache hit rate"""
        cache = QueryCache(ttl=300)
        
        query = "SELECT * FROM transactions WHERE id = %s"
        result = [{'id': 'TXN123', 'amount': 100}]
        
        # Set cache
        cache.set(query, ('TXN123',), result)
        
        # Multiple gets (hits)
        for _ in range(5):
            cache.get(query, ('TXN123',))
        
        # Misses
        for i in range(3):
            cache.get(query, (f'TXN{i}',))
        
        stats = cache.get_stats()
        assert stats['hits'] == 5
        assert stats['misses'] == 3
        assert stats['hit_rate'] > 0.5


@pytest.mark.integration
class TestDatabaseOptimizationIntegration:
    """Integration tests for database optimization"""
    
    @pytest.mark.skip(reason="Requires running PostgreSQL instance")
    def test_connection_pool_under_load(self):
        """Test connection pool performance under load"""
        # This would test actual connection pool with concurrent requests
        pass
    
    @pytest.mark.skip(reason="Requires running PostgreSQL instance")
    def test_query_performance_with_indexes(self):
        """Test query performance improvement with indexes"""
        # This would benchmark queries before and after index creation
        pass
    
    @pytest.mark.skip(reason="Requires running PostgreSQL instance")
    def test_cache_effectiveness(self):
        """Test cache effectiveness in reducing database load"""
        # This would measure database load with and without caching
        pass
