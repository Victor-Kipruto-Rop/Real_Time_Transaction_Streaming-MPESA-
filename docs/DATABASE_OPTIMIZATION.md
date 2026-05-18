"""
DATABASE OPTIMIZATION GUIDE

M-Pesa Real-Time Transaction Streaming Platform
Database Performance Optimization Strategy
"""

# DATABASE ARCHITECTURE OVERVIEW
# ================================

The platform uses PostgreSQL 15 for data storage with the following components:
- Local development: Docker PostgreSQL 15-alpine
- Production: AWS RDS PostgreSQL 15 with IAM authentication
- Caching: Redis 7 for query result caching
- Connection pooling: psycopg2 SimpleConnectionPool

Database name: mpesa_analytics
Primary tables:
  - stg_mpesa_raw: Raw M-Pesa events from webhooks
  - stg_c2b_transactions: Customer-to-Business confirmed transactions
  - mart_daily_transactions: Daily aggregated summaries (pre-computed)
  - mart_county_heatmap: County-level transaction heatmaps


# PERFORMANCE OPTIMIZATION LAYERS
# ================================

1. CONNECTION POOLING (db_pool.py)
   - Reduces connection overhead
   - Maintains persistent connections
   - Minimum 2, Maximum 10 connections (configurable)
   - Automatic reconnection on failure

2. QUERY OPTIMIZATION (db_queries.py)
   - Parameterized queries (SQL injection protection)
   - Pre-built optimized query patterns
   - Query performance monitoring
   - Index recommendations

3. CACHING STRATEGY (db_cache.py)
   - Two-tier caching:
     * L1: In-memory LRU cache (fast, local)
     * L2: Redis distributed cache (shared, persistent)
   - 5-minute default TTL (configurable per query)
   - Automatic cache invalidation on data updates


# RECOMMENDED DATABASE INDEXES
# =============================

PRIMARY LOOKUPS:
  idx_stg_c2b_transactions_transaction_id (UNIQUE)
    - Fast lookup by transaction ID
    - Used by: get_transaction_by_id()

CUSTOMER QUERIES:
  idx_stg_c2b_transactions_customer_phone_number
    - Filter transactions by customer
    - Used by: get_transactions_by_phone()

TIME-BASED QUERIES:
  idx_stg_c2b_transactions_transaction_date
    - Range queries for date-based filtering
    - Used by: get_daily_summary(), get_hourly_trend()

MERCHANT QUERIES:
  idx_stg_c2b_transactions_account_reference
    - Filter by merchant/account
    - Used by: get_top_merchants()

COMPOSITE INDEXES:
  idx_stg_c2b_transactions_customer_phone_number_transaction_date
    - Optimized for: customer + date range queries
    - Common pattern: get transactions for customer on specific date


# QUICK START: ENABLE OPTIMIZATION
# ==================================

1. Start Docker infrastructure:
   make infra-up

2. Setup connection pooling:
   from ingestion.db_pool import get_pooled_connection
   
   with get_pooled_connection() as conn:
       cur = conn.cursor()
       cur.execute('SELECT * FROM transactions')
       data = cur.fetchall()

3. Create recommended indexes:
   make db-indexes

4. Use optimized queries:
   from ingestion.db_queries import DatabaseQueries
   
   # All queries already optimized
   results = DatabaseQueries.get_transaction_by_id('TX123')
   summary = DatabaseQueries.get_daily_summary('2026-05-18')

5. Enable caching:
   from ingestion.db_cache import cached_query
   
   @cached_query(ttl=600)  # Cache for 10 minutes
   def my_query(param):
       return DatabaseQueries.execute_query(...)

6. Monitor performance:
   from ingestion.db_queries import QueryPerformanceMonitor
   
   stats = QueryPerformanceMonitor.get_performance_summary()


# PERFORMANCE TESTING
# ====================

Run all optimization tests:
  make test-db-optimize

Run with coverage report:
  make test-db-optimize-cov

Test modules:
  - tests/test_db_optimization.py (20+ test cases)
  - tests/test_rds_connection.py (13 test cases)

Key test coverage:
  ✓ Connection pooling and reuse
  ✓ Query parameter binding (SQL injection prevention)
  ✓ Cache management (set, get, invalidate, expire)
  ✓ In-memory and Redis cache layers
  ✓ Query performance monitoring
  ✓ Error handling and recovery


# PERFORMANCE METRICS & MONITORING
# ==================================

1. Connection Pool Metrics:
   - Active connections
   - Available connections
   - Connection wait time
   - Reconnection attempts

2. Query Performance:
   - Query execution time (ms)
   - Slowest queries (tracked)
   - Average query time
   - Total query time

3. Cache Metrics:
   - Cache hit rate
   - Cache miss rate
   - In-memory cache size
   - Redis memory usage
   - Cache TTL effectiveness

Monitor in code:
  from ingestion.db_queries import QueryPerformanceMonitor
  from ingestion.db_cache import get_cache_manager
  
  # Get performance summary
  perf = QueryPerformanceMonitor.get_performance_summary()
  print(f"Avg query time: {perf['avg_time']:.3f}s")
  
  # Get cache stats
  cache = get_cache_manager()
  stats = cache.get_stats()
  print(f"Cache hits: {stats['in_memory_size']} entries")


# PRODUCTION DEPLOYMENT CHECKLIST
# ================================

Before deploying to production:

1. Database Configuration:
   ☐ AWS RDS PostgreSQL 15 provisioned
   ☐ IAM authentication configured
   ☐ Security groups allow inbound traffic
   ☐ Parameter groups optimized for workload
   ☐ Multi-AZ replication enabled
   ☐ Automated backups configured

2. Indexes:
   ☐ All recommended indexes created
   ☐ Index fragmentation < 20%
   ☐ Vacuum and analyze completed
   ☐ Maintenance windows scheduled

3. Connection Pooling:
   ☐ Pool size tuned for workload
   ☐ Connection timeout configured
   ☐ Idle connection cleanup enabled
   ☐ Connection reset on error

4. Caching:
   ☐ Redis cluster provisioned
   ☐ Cache eviction policy set (LRU)
   ☐ Cache TTL values optimized
   ☐ Monitoring and alerts configured

5. Monitoring & Alerts:
   ☐ Query performance metrics collected
   ☐ Slow query log enabled (> 100ms)
   ☐ Connection pool alerts
   ☐ Cache hit/miss rate alerts
   ☐ Database CPU/memory alerts
   ☐ Disk space monitoring

6. Testing:
   ☐ Load test with expected traffic
   ☐ Failover tested
   ☐ Cache invalidation tested
   ☐ Query timeouts tested
   ☐ Connection pool exhaustion tested


# OPTIMIZATION STRATEGIES BY USE CASE
# ====================================

HIGH-FREQUENCY LOOKUPS (transaction by ID):
  - Use: get_transaction_by_id() with unique index
  - Cache: YES (TTL: 1 hour)
  - Pool: Small (2-5 connections)
  - Expected: < 10ms response time

AGGREGATED QUERIES (daily summaries):
  - Use: get_daily_summary() on pre-aggregated table
  - Cache: YES (TTL: 1 hour)
  - Pool: Small (2-5 connections)
  - Expected: < 50ms response time

CUSTOMER HISTORY (all transactions for customer):
  - Use: get_transactions_by_phone() with pagination
  - Cache: YES (TTL: 30 minutes)
  - Pool: Medium (5-10 connections)
  - Expected: < 200ms response time

REAL-TIME ANALYTICS (hourly trends):
  - Use: get_hourly_trend() 
  - Cache: CONDITIONAL (TTL: 5 minutes)
  - Pool: Medium (5-10 connections)
  - Expected: < 500ms response time

BATCH OPERATIONS (nightly imports):
  - Use: Connection pooling with batch inserts
  - Cache: Invalidate after completion
  - Pool: Large (10-20 connections)
  - Expected: Throughput-optimized


# TROUBLESHOOTING SLOW QUERIES
# =============================

Symptom: High query latency
Debug steps:
  1. Check connection pool status:
     from ingestion.db_pool import DatabasePool
     pool = DatabasePool.get_instance()
     print(pool._pool.getsize())  # Should be < max_connections
  
  2. Check for table scans:
     EXPLAIN ANALYZE SELECT ... FROM transactions ...
  
  3. Check cache effectiveness:
     cache = get_cache_manager()
     print(cache.get_stats())
  
  4. Monitor slow queries:
     SET log_min_duration_statement = 100;  -- Log queries > 100ms

Common causes and fixes:
  - Missing index: CREATE INDEX (see recommendations)
  - Cache not working: Check Redis connection
  - Connection pool full: Increase max_connections
  - Large result set: Use pagination or materialized view


# COST OPTIMIZATION FOR AWS RDS
# ===============================

RDS Instance Type Selection:
  - Development: db.t3.micro (< 10 transactions/min)
  - Production: db.r6g.large or larger (CPU/RAM optimized)
  - With caching: Smaller instance due to reduced query load

Estimated savings with optimization:
  - Connection pooling: 30-40% fewer connections
  - Query caching: 50-70% fewer database requests
  - Index optimization: 60-80% faster queries
  - Combined: 70-90% reduction in database load


# REFERENCES & DOCUMENTATION
# ============================

Files:
  - ingestion/rds_connection.py: AWS RDS IAM authentication
  - ingestion/db_pool.py: Connection pooling implementation
  - ingestion/db_queries.py: Optimized query patterns
  - ingestion/db_cache.py: Caching layer (in-memory + Redis)
  - tests/test_db_optimization.py: Comprehensive test suite

Make commands:
  - make db-optimize: Show optimization options
  - make test-db-optimize: Run all tests
  - make db-health: Check database health
  - make db-indexes: Create recommended indexes

PostgreSQL Tuning:
  - shared_buffers: 25% of RAM
  - effective_cache_size: 50-75% of RAM
  - maintenance_work_mem: 256MB - 1GB
  - work_mem: (total_RAM - shared_buffers) / max_connections

Redis Configuration:
  - maxmemory: Set to <80% of available RAM
  - maxmemory-policy: allkeys-lru for auto-eviction
  - appendonly: yes (for persistence)
  - appendfsync: everysec (balance safety/performance)
"""

# This is a documentation module. Import for reference:
# from ingestion import db_optimization_guide
# Or use: make db-optimize to display this information
