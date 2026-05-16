"""
Health checks for M-Pesa streaming pipeline.

Monitors system health including Kafka connectivity, database status,
message lag, and webhook receiver availability.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import psycopg2

try:
    from confluent_kafka import Consumer, KafkaException
except Exception:
    Consumer = None
    KafkaException = Exception

logger = logging.getLogger(__name__)


class HealthChecker:
    """Monitor pipeline health across all components."""

    def __init__(self):
        """Initialize health checker."""
        self.kafka_brokers = os.getenv("KAFKA_BROKERS", "localhost:9092")
        self.postgres_dsn = self._build_postgres_dsn()

    def _build_postgres_dsn(self) -> Optional[str]:
        """Build PostgreSQL connection string from environment."""
        if os.getenv("DATABASE_URL"):
            return os.getenv("DATABASE_URL")

        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "mpesa")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "")

        if not all([host, port, db, user]):
            return None

        return f"dbname={db} user={user} password={password} host={host} port={port}"

    def check_kafka_connectivity(self) -> Dict[str, Any]:
        """Check Kafka broker connectivity."""
        try:
            if Consumer is None:
                return {
                    "status": "error",
                    "message": "confluent_kafka not installed",
                    "timestamp": datetime.utcnow().isoformat(),
                }

            conf = {
                "bootstrap.servers": self.kafka_brokers,
                "group.id": "health-check",
                "auto.offset.reset": "earliest",
            }

            consumer = Consumer(conf)
            metadata = consumer.list_topics(timeout=5)
            consumer.close()

            topics = list(metadata.topics.keys())
            return {
                "status": "healthy",
                "brokers": self.kafka_brokers,
                "topics_count": len(topics),
                "topics": topics[:10],
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Kafka connectivity check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "brokers": self.kafka_brokers,
                "timestamp": datetime.utcnow().isoformat(),
            }

    def check_database_connection(self) -> Dict[str, Any]:
        """Check PostgreSQL database connectivity."""
        try:
            if not self.postgres_dsn:
                return {
                    "status": "error",
                    "message": "PostgreSQL DSN not configured",
                    "timestamp": datetime.utcnow().isoformat(),
                }

            conn = psycopg2.connect(self.postgres_dsn)
            cursor = conn.cursor()

            # Test connectivity
            cursor.execute("SELECT 1")
            cursor.fetchone()

            # Get database size
            cursor.execute(
                """
                SELECT pg_size_pretty(pg_database_size(datname))
                FROM pg_database WHERE datname = current_database()
            """
            )
            size_row = cursor.fetchone()
            db_size = size_row[0] if size_row else "N/A"

            cursor.close()
            conn.close()

            return {
                "status": "healthy",
                "database": self.postgres_dsn.split("dbname=")[1].split()[0],
                "database_size": db_size,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Database connectivity check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def check_message_lag(self) -> Dict[str, Any]:
        """Check Kafka consumer lag for M-Pesa topic."""
        try:
            if Consumer is None:
                return {
                    "status": "error",
                    "message": "confluent_kafka not installed",
                    "timestamp": datetime.utcnow().isoformat(),
                }

            conf = {
                "bootstrap.servers": self.kafka_brokers,
                "group.id": "mpesa_consumer_group",
                "auto.offset.reset": "earliest",
            }

            consumer = Consumer(conf)
            consumer.subscribe(["mpesa-transactions"])

            # Poll to trigger metadata fetch
            consumer.poll(timeout=1)

            # Get committed offsets
            partitions = consumer.assignment()
            lag_info = {}

            for partition in partitions:
                committed = consumer.committed(partition)
                position = consumer.position(partition)

                if committed and position:
                    lag = position - committed
                    lag_info[f"partition_{partition.partition}"] = {
                        "committed_offset": committed,
                        "current_position": position,
                        "lag": lag,
                    }

            consumer.close()

            total_lag = sum(p.get("lag", 0) for p in lag_info.values())

            return {
                "status": "healthy",
                "topic": "mpesa-transactions",
                "total_lag": total_lag,
                "partitions": lag_info,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Message lag check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def check_transaction_volume(self, hours: int = 1) -> Dict[str, Any]:
        """Check recent transaction volume."""
        try:
            if not self.postgres_dsn:
                return {
                    "status": "error",
                    "message": "PostgreSQL DSN not configured",
                    "timestamp": datetime.utcnow().isoformat(),
                }

            conn = psycopg2.connect(self.postgres_dsn)
            cursor = conn.cursor()

            # Get transaction volume in last N hours
            since = datetime.utcnow() - timedelta(hours=hours)
            cursor.execute(
                """
                SELECT COUNT(*) as transaction_count,
                       COUNT(DISTINCT phone_number) as unique_customers,
                       SUM(CAST(amount AS NUMERIC)) as total_amount,
                       AVG(CAST(amount AS NUMERIC)) as avg_amount,
                       MAX(CAST(amount AS NUMERIC)) as max_amount,
                       MIN(CAST(amount AS NUMERIC)) as min_amount
                FROM mpesa_transactions_raw
                WHERE received_at > %s
            """,
                (since,),
            )

            row = cursor.fetchone()
            cursor.close()
            conn.close()

            return {
                "status": "healthy",
                "time_window_hours": hours,
                "transaction_count": row[0] if row else 0,
                "unique_customers": row[1] if row else 0,
                "total_amount_ksh": float(row[2]) if row and row[2] else 0,
                "avg_amount_ksh": float(row[3]) if row and row[3] else 0,
                "max_amount_ksh": float(row[4]) if row and row[4] else 0,
                "min_amount_ksh": float(row[5]) if row and row[5] else 0,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Transaction volume check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def check_data_staleness(self) -> Dict[str, Any]:
        """Check how fresh the data is."""
        try:
            if not self.postgres_dsn:
                return {
                    "status": "error",
                    "message": "PostgreSQL DSN not configured",
                    "timestamp": datetime.utcnow().isoformat(),
                }

            conn = psycopg2.connect(self.postgres_dsn)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT MAX(received_at) as last_transaction_time
                FROM mpesa_transactions_raw
            """
            )

            result = cursor.fetchone()
            last_transaction = result[0] if result and result[0] else None

            cursor.close()
            conn.close()

            if last_transaction:
                staleness = datetime.utcnow() - last_transaction
                status = "healthy" if staleness.total_seconds() < 300 else "warning"

                return {
                    "status": status,
                    "last_transaction_time": last_transaction.isoformat(),
                    "staleness_seconds": int(staleness.total_seconds()),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                return {
                    "status": "warning",
                    "message": "No transactions found in database",
                    "timestamp": datetime.utcnow().isoformat(),
                }
        except Exception as e:
            logger.error(f"Data staleness check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def get_full_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "kafka_connectivity": self.check_kafka_connectivity(),
            "database_connection": self.check_database_connection(),
            "message_lag": self.check_message_lag(),
            "transaction_volume": self.check_transaction_volume(hours=1),
            "data_staleness": self.check_data_staleness(),
        }


def health_check_endpoint() -> Dict[str, Any]:
    """Flask endpoint for health checks."""
    checker = HealthChecker()
    return checker.get_full_health_report()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    checker = HealthChecker()
    report = checker.get_full_health_report()

    import json

    print(json.dumps(report, indent=2, default=str))
