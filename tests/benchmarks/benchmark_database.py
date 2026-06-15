"""
Database Performance Benchmarks

Tests PostgreSQL query performance and connection pooling.
"""

import time
import statistics
import psycopg2
from psycopg2 import pool
from typing import Dict, List
import random
import json


class DatabaseBenchmark:
    """Benchmark database performance"""

    def __init__(
        self,
        host="localhost",
        port=5432,
        database="mpesa_analytics",
        user="data_engineer",
        password="change_me",
    ):
        self.connection_params = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password,
        }

    def benchmark_connection_time(self, num_connections: int = 100) -> Dict:
        """
        Benchmark connection establishment time

        Args:
            num_connections: Number of connections to test

        Returns:
            Dict with benchmark results
        """
        connection_times = []

        for _ in range(num_connections):
            start = time.time()
            conn = psycopg2.connect(**self.connection_params)
            conn.close()
            duration = (time.time() - start) * 1000  # ms
            connection_times.append(duration)

        return {
            "test": "connection_time",
            "connections": num_connections,
            "avg_time_ms": round(statistics.mean(connection_times), 2),
            "median_time_ms": round(statistics.median(connection_times), 2),
            "p95_time_ms": round(statistics.quantiles(connection_times, n=20)[18], 2),
            "min_time_ms": round(min(connection_times), 2),
            "max_time_ms": round(max(connection_times), 2),
        }

    def benchmark_connection_pool(
        self, pool_size: int = 10, num_queries: int = 1000
    ) -> Dict:
        """
        Benchmark connection pooling performance

        Args:
            pool_size: Size of connection pool
            num_queries: Number of queries to execute

        Returns:
            Dict with benchmark results
        """
        # Create connection pool
        connection_pool = psycopg2.pool.SimpleConnectionPool(
            1, pool_size, **self.connection_params
        )

        query_times = []

        start_time = time.time()

        for _ in range(num_queries):
            query_start = time.time()

            conn = connection_pool.getconn()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            connection_pool.putconn(conn)

            query_time = (time.time() - query_start) * 1000
            query_times.append(query_time)

        total_time = time.time() - start_time

        connection_pool.closeall()

        return {
            "test": "connection_pool",
            "pool_size": pool_size,
            "queries": num_queries,
            "total_time_seconds": round(total_time, 2),
            "throughput_qps": round(num_queries / total_time, 2),
            "avg_query_time_ms": round(statistics.mean(query_times), 2),
            "median_query_time_ms": round(statistics.median(query_times), 2),
            "p95_query_time_ms": round(statistics.quantiles(query_times, n=20)[18], 2),
        }

    def benchmark_insert_performance(self, num_inserts: int = 1000) -> Dict:
        """
        Benchmark INSERT performance

        Args:
            num_inserts: Number of records to insert

        Returns:
            Dict with benchmark results
        """
        conn = psycopg2.connect(**self.connection_params)
        cursor = conn.cursor()

        # Create test table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS benchmark_test (
                id SERIAL PRIMARY KEY,
                transaction_id VARCHAR(50),
                amount DECIMAL(15,2),
                phone_number VARCHAR(15),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        # Benchmark inserts
        insert_times = []

        for i in range(num_inserts):
            start = time.time()

            cursor.execute(
                """
                INSERT INTO benchmark_test (transaction_id, amount, phone_number)
                VALUES (%s, %s, %s)
            """,
                (f"TXN{i:010d}", random.uniform(100, 10000), f"25471234{i%10000:04d}"),
            )

            conn.commit()

            duration = (time.time() - start) * 1000
            insert_times.append(duration)

        # Cleanup
        cursor.execute("DROP TABLE benchmark_test")
        conn.commit()
        cursor.close()
        conn.close()

        return {
            "test": "insert_performance",
            "inserts": num_inserts,
            "avg_time_ms": round(statistics.mean(insert_times), 2),
            "median_time_ms": round(statistics.median(insert_times), 2),
            "p95_time_ms": round(statistics.quantiles(insert_times, n=20)[18], 2),
            "throughput_ops": round(num_inserts / (sum(insert_times) / 1000), 2),
        }

    def benchmark_batch_insert(
        self, batch_size: int = 100, num_batches: int = 10
    ) -> Dict:
        """
        Benchmark batch INSERT performance

        Args:
            batch_size: Number of records per batch
            num_batches: Number of batches

        Returns:
            Dict with benchmark results
        """
        conn = psycopg2.connect(**self.connection_params)
        cursor = conn.cursor()

        # Create test table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS benchmark_test (
                id SERIAL PRIMARY KEY,
                transaction_id VARCHAR(50),
                amount DECIMAL(15,2),
                phone_number VARCHAR(15)
            )
        """)
        conn.commit()

        batch_times = []
        total_records = 0

        for batch_num in range(num_batches):
            # Prepare batch data
            values = []
            for i in range(batch_size):
                record_num = batch_num * batch_size + i
                values.append(
                    (
                        f"TXN{record_num:010d}",
                        random.uniform(100, 10000),
                        f"25471234{record_num%10000:04d}",
                    )
                )

            start = time.time()

            # Execute batch insert
            cursor.executemany(
                """
                INSERT INTO benchmark_test (transaction_id, amount, phone_number)
                VALUES (%s, %s, %s)
            """,
                values,
            )

            conn.commit()

            duration = (time.time() - start) * 1000
            batch_times.append(duration)
            total_records += batch_size

        # Cleanup
        cursor.execute("DROP TABLE benchmark_test")
        conn.commit()
        cursor.close()
        conn.close()

        return {
            "test": "batch_insert",
            "batch_size": batch_size,
            "num_batches": num_batches,
            "total_records": total_records,
            "avg_batch_time_ms": round(statistics.mean(batch_times), 2),
            "total_time_seconds": round(sum(batch_times) / 1000, 2),
            "throughput_records_per_sec": round(
                total_records / (sum(batch_times) / 1000), 2
            ),
        }

    def benchmark_select_performance(self, num_queries: int = 100) -> Dict:
        """
        Benchmark SELECT query performance

        Args:
            num_queries: Number of queries to execute

        Returns:
            Dict with benchmark results
        """
        conn = psycopg2.connect(**self.connection_params)
        cursor = conn.cursor()

        query_times = []

        for _ in range(num_queries):
            start = time.time()

            cursor.execute("""
                SELECT COUNT(*), SUM(amount), AVG(amount)
                FROM mpesa_transactions_raw
                WHERE transaction_time >= NOW() - INTERVAL '7 days'
            """)

            cursor.fetchone()

            duration = (time.time() - start) * 1000
            query_times.append(duration)

        cursor.close()
        conn.close()

        return {
            "test": "select_performance",
            "queries": num_queries,
            "avg_time_ms": round(statistics.mean(query_times), 2),
            "median_time_ms": round(statistics.median(query_times), 2),
            "p95_time_ms": round(statistics.quantiles(query_times, n=20)[18], 2),
            "p99_time_ms": round(statistics.quantiles(query_times, n=100)[98], 2),
            "min_time_ms": round(min(query_times), 2),
            "max_time_ms": round(max(query_times), 2),
        }

    def benchmark_complex_query(self, num_queries: int = 50) -> Dict:
        """
        Benchmark complex query with joins and aggregations

        Args:
            num_queries: Number of queries to execute

        Returns:
            Dict with benchmark results
        """
        conn = psycopg2.connect(**self.connection_params)
        cursor = conn.cursor()

        query_times = []

        for _ in range(num_queries):
            start = time.time()

            cursor.execute("""
                SELECT 
                    phone_number,
                    COUNT(*) as transaction_count,
                    SUM(amount) as total_amount,
                    AVG(amount) as avg_amount,
                    MAX(amount) as max_amount
                FROM mpesa_transactions_raw
                WHERE transaction_time >= NOW() - INTERVAL '30 days'
                GROUP BY phone_number
                HAVING COUNT(*) > 5
                ORDER BY total_amount DESC
                LIMIT 100
            """)

            cursor.fetchall()

            duration = (time.time() - start) * 1000
            query_times.append(duration)

        cursor.close()
        conn.close()

        return {
            "test": "complex_query",
            "queries": num_queries,
            "avg_time_ms": round(statistics.mean(query_times), 2),
            "median_time_ms": round(statistics.median(query_times), 2),
            "p95_time_ms": round(statistics.quantiles(query_times, n=20)[18], 2),
            "min_time_ms": round(min(query_times), 2),
            "max_time_ms": round(max(query_times), 2),
        }


def run_all_benchmarks():
    """Run all database benchmarks"""
    benchmark = DatabaseBenchmark()

    results = []

    print("1. Testing Connection Time...")
    result = benchmark.benchmark_connection_time(100)
    results.append(result)
    print(json.dumps(result, indent=2))

    print("\n2. Testing Connection Pool...")
    result = benchmark.benchmark_connection_pool(10, 1000)
    results.append(result)
    print(json.dumps(result, indent=2))

    print("\n3. Testing Insert Performance...")
    result = benchmark.benchmark_insert_performance(1000)
    results.append(result)
    print(json.dumps(result, indent=2))

    print("\n4. Testing Batch Insert...")
    result = benchmark.benchmark_batch_insert(100, 10)
    results.append(result)
    print(json.dumps(result, indent=2))

    print("\n5. Testing Select Performance...")
    result = benchmark.benchmark_select_performance(100)
    results.append(result)
    print(json.dumps(result, indent=2))

    print("\n6. Testing Complex Query...")
    result = benchmark.benchmark_complex_query(50)
    results.append(result)
    print(json.dumps(result, indent=2))

    return results


if __name__ == "__main__":
    results = run_all_benchmarks()

    print("\n" + "=" * 60)
    print("DATABASE BENCHMARK SUMMARY")
    print("=" * 60)

    for result in results:
        print(f"\n{result['test'].upper()}:")
        for key, value in result.items():
            if key != "test":
                print(f"  {key}: {value}")
