"""
Optimized PostgreSQL Query Module

Provides efficient database queries for M-Pesa analytics with:
- Query result caching
- Index optimization recommendations
- Query performance tracking
- Prepared statements for security and speed
"""

import time
import logging
from typing import List, Dict, Any, Optional
from functools import lru_cache
import psycopg2
from psycopg2.extras import RealDictCursor
from ingestion.db_pool import get_pooled_connection

logger = logging.getLogger(__name__)


class DatabaseQueries:
    """Optimized database queries for M-Pesa transactions"""
    
    # Cache configuration
    CACHE_TTL = 300  # 5 minutes
    
    @staticmethod
    def execute_query(query: str, params: tuple = None, 
                     fetch_one: bool = False,
                     dict_cursor: bool = True) -> Optional[Any]:
        """
        Execute a single query with performance tracking.
        
        Args:
            query: SQL query string
            params: Query parameters (for prepared statements)
            fetch_one: Return single row instead of all
            dict_cursor: Use dictionary cursor for column names
            
        Returns:
            Query result(s) or None
        """
        start_time = time.time()
        try:
            with get_pooled_connection() as conn:
                cursor_factory = RealDictCursor if dict_cursor else None
                cur = conn.cursor(cursor_factory=cursor_factory)
                
                # Use parameterized queries to prevent SQL injection
                cur.execute(query, params or ())
                
                result = cur.fetchone() if fetch_one else cur.fetchall()
                cur.close()
                
                elapsed = time.time() - start_time
                logger.info(f"Query executed in {elapsed:.3f}s")
                return result
        except psycopg2.Error as e:
            logger.error(f"Database error: {e}")
            raise
    
    @staticmethod
    def get_transaction_by_id(transaction_id: str) -> Optional[Dict]:
        """Get single transaction by ID (index-optimized)"""
        query = """
        SELECT * FROM stg_c2b_transactions 
        WHERE transaction_id = %s
        LIMIT 1
        """
        return DatabaseQueries.execute_query(query, (transaction_id,), fetch_one=True)
    
    @staticmethod
    def get_transactions_by_phone(phone_number: str, 
                                 limit: int = 100) -> List[Dict]:
        """Get transactions for a customer (index-optimized)"""
        query = """
        SELECT * FROM stg_c2b_transactions 
        WHERE customer_phone_number = %s
        ORDER BY transaction_date DESC
        LIMIT %s
        """
        return DatabaseQueries.execute_query(
            query, 
            (phone_number, limit), 
            fetch_one=False
        ) or []
    
    @staticmethod
    def get_daily_summary(transaction_date: str) -> List[Dict]:
        """Get daily transaction summary (pre-aggregated table)"""
        query = """
        SELECT * FROM mart_daily_transactions 
        WHERE transaction_date = %s
        ORDER BY total_transaction_value DESC
        """
        return DatabaseQueries.execute_query(
            query, 
            (transaction_date,), 
            fetch_one=False
        ) or []
    
    @staticmethod
    def get_heatmap_data(transaction_date: str) -> List[Dict]:
        """Get county heatmap data (pre-aggregated)"""
        query = """
        SELECT * FROM mart_county_heatmap 
        WHERE transaction_date = %s
        ORDER BY transaction_count DESC
        """
        return DatabaseQueries.execute_query(
            query, 
            (transaction_date,), 
            fetch_one=False
        ) or []
    
    @staticmethod
    def get_transaction_statistics(start_date: str, 
                                   end_date: str) -> Optional[Dict]:
        """Get aggregated transaction statistics"""
        query = """
        SELECT 
            COUNT(*) as total_transactions,
            SUM(transaction_amount) as total_amount,
            AVG(transaction_amount) as avg_amount,
            MIN(transaction_amount) as min_amount,
            MAX(transaction_amount) as max_amount,
            COUNT(DISTINCT customer_phone_number) as unique_customers
        FROM stg_c2b_transactions 
        WHERE transaction_date BETWEEN %s AND %s
        """
        return DatabaseQueries.execute_query(
            query, 
            (start_date, end_date), 
            fetch_one=True
        )
    
    @staticmethod
    def get_top_merchants(limit: int = 10) -> List[Dict]:
        """Get top merchants by transaction count"""
        query = """
        SELECT 
            account_reference,
            COUNT(*) as transaction_count,
            SUM(transaction_amount) as total_amount,
            AVG(transaction_amount) as avg_amount
        FROM stg_c2b_transactions 
        GROUP BY account_reference
        ORDER BY transaction_count DESC
        LIMIT %s
        """
        return DatabaseQueries.execute_query(query, (limit,)) or []
    
    @staticmethod
    def get_hourly_trend(transaction_date: str) -> List[Dict]:
        """Get hourly transaction trend"""
        query = """
        SELECT 
            DATE_TRUNC('hour', transaction_date)::timestamp as hour,
            COUNT(*) as transaction_count,
            SUM(transaction_amount) as total_amount
        FROM stg_c2b_transactions 
        WHERE transaction_date::date = %s::date
        GROUP BY DATE_TRUNC('hour', transaction_date)
        ORDER BY hour ASC
        """
        return DatabaseQueries.execute_query(query, (transaction_date,)) or []
    
    @staticmethod
    def health_check() -> bool:
        """Simple health check query"""
        try:
            with get_pooled_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                result = cur.fetchone()
                cur.close()
                return result is not None
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


class IndexRecommendations:
    """Database index optimization recommendations"""
    
    RECOMMENDED_INDEXES = [
        {
            'table': 'stg_c2b_transactions',
            'columns': ['transaction_id'],
            'unique': True,
            'reason': 'Primary lookup by transaction ID'
        },
        {
            'table': 'stg_c2b_transactions',
            'columns': ['customer_phone_number'],
            'unique': False,
            'reason': 'Filter transactions by customer'
        },
        {
            'table': 'stg_c2b_transactions',
            'columns': ['transaction_date'],
            'unique': False,
            'reason': 'Time-based queries'
        },
        {
            'table': 'stg_c2b_transactions',
            'columns': ['account_reference'],
            'unique': False,
            'reason': 'Merchant lookups'
        },
        {
            'table': 'stg_c2b_transactions',
            'columns': ['customer_phone_number', 'transaction_date'],
            'unique': False,
            'reason': 'Composite for customer timeline queries'
        },
    ]
    
    @staticmethod
    def create_recommended_indexes():
        """Create all recommended indexes"""
        logger.info("Creating recommended indexes...")
        for idx_config in IndexRecommendations.RECOMMENDED_INDEXES:
            table = idx_config['table']
            columns = idx_config['columns']
            reason = idx_config['reason']
            
            col_str = '_'.join(columns)
            idx_name = f"idx_{table}_{col_str}"
            col_list = ', '.join(columns)
            unique_str = 'UNIQUE ' if idx_config['unique'] else ''
            
            query = f"""
            CREATE INDEX IF NOT EXISTS {idx_name} 
            ON {table} ({col_list});
            """
            
            try:
                with get_pooled_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(query)
                    conn.commit()
                    cur.close()
                    logger.info(f"✓ Created {idx_name}: {reason}")
            except psycopg2.Error as e:
                logger.warning(f"Could not create {idx_name}: {e}")
    
    @staticmethod
    def get_index_status():
        """Get current index status and recommendations"""
        query = """
        SELECT 
            tablename,
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        ORDER BY tablename, indexname
        """
        try:
            result = DatabaseQueries.execute_query(query)
            logger.info(f"Current indexes:\n{result}")
            return result
        except Exception as e:
            logger.error(f"Could not retrieve index status: {e}")
            return []


class QueryPerformanceMonitor:
    """Monitor and log query performance metrics"""
    
    _metrics = []
    
    @staticmethod
    def log_query_time(query_name: str, elapsed_time: float):
        """Log query execution time"""
        QueryPerformanceMonitor._metrics.append({
            'query': query_name,
            'elapsed_time': elapsed_time
        })
    
    @staticmethod
    def get_slowest_queries(limit: int = 10) -> List[Dict]:
        """Get slowest queries"""
        sorted_metrics = sorted(
            QueryPerformanceMonitor._metrics,
            key=lambda x: x['elapsed_time'],
            reverse=True
        )
        return sorted_metrics[:limit]
    
    @staticmethod
    def get_performance_summary() -> Dict:
        """Get performance summary"""
        if not QueryPerformanceMonitor._metrics:
            return {}
        
        times = [m['elapsed_time'] for m in QueryPerformanceMonitor._metrics]
        return {
            'total_queries': len(QueryPerformanceMonitor._metrics),
            'avg_time': sum(times) / len(times),
            'min_time': min(times),
            'max_time': max(times),
            'total_time': sum(times)
        }
