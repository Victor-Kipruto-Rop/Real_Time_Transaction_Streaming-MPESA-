"""
Kafka consumer for Project 01 (refactored with class-based API).

Consumes JSON events produced by `ingestion/webhook_receiver.py` and lands them
into Postgres (`mpesa_transactions_raw`) for downstream dbt models.
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterator, Optional

from psycopg2 import pool

from schemas.transaction_schema import MpesaEvent

try:
    from confluent_kafka import Consumer, KafkaException
except Exception:  # pragma: no cover
    Consumer = None  # type: ignore[assignment,misc]
    KafkaException = Exception  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_DARAJA_TIME_FORMAT = "%Y%m%d%H%M%S"


@dataclass(frozen=True)
class ConsumerConfig:
    """Kafka consumer configuration."""

    brokers: str
    topic: str
    group_id: str
    postgres_dsn: Optional[str] = None
    batch_size: int = 50
    max_poll_interval_ms: int = 300000


def postgres_dsn_from_env() -> Optional[str]:
    """Build PostgreSQL connection string from environment."""
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")

    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")
    db = os.getenv("POSTGRES_DB")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")

    if not all([host, port, db, user, password]):
        return None

    return f"dbname={db} user={user} password={password} host={host} port={port}"


def _coerce_legacy_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce older event shapes into the current MpesaEvent contract."""
    if payload.get("event_type") == "c2b_transaction":
        payload = dict(payload)
        payload["event_type"] = "c2b_confirmation"
        if (
            "amount" in payload
            and payload["amount"] is not None
            and not isinstance(payload["amount"], str)
        ):
            payload["amount"] = str(payload["amount"])
    return payload


def _parse_transaction_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value, _DARAJA_TIME_FORMAT)
    except Exception:
        try:
            # Accept ISO 8601 timestamps if present (e.g. demo payloads).
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            raise ValueError(f"Unsupported transaction_time format: {value}")


class MpesaKafkaConsumer:
    """Class-based Kafka consumer for M-Pesa transactions."""

    def __init__(
        self,
        brokers: str = "",
        topic: str = "mpesa-transactions",
        group_id: str = "mpesa_consumer_group",
        postgres_dsn: Optional[str] = None,
        batch_size: int = 50,
    ):
        """
        Initialize the Kafka consumer.

        Args:
            brokers: Comma-separated Kafka brokers (default from env)
            topic: Kafka topic to consume from
            group_id: Consumer group ID
            postgres_dsn: PostgreSQL connection string (default from env)
            batch_size: Batch size for database inserts
        """
        self.brokers = brokers or os.getenv("KAFKA_BROKERS", "localhost:9092")
        self.topic = topic or os.getenv("KAFKA_TOPIC_TRANSACTIONS", "mpesa-transactions")
        self.group_id = group_id or os.getenv("KAFKA_GROUP_ID", "mpesa_consumer_group")
        self.postgres_dsn = postgres_dsn or postgres_dsn_from_env()
        self.batch_size = batch_size

        if Consumer is None:
            raise RuntimeError(
                "confluent-kafka is not installed. Install `requirements.txt` for Project 01."
            )

        self.consumer = Consumer(
            {
                "bootstrap.servers": self.brokers,
                "group.id": self.group_id,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": True,
                "max.poll.interval.ms": 300000,
            }
        )
        self.consumer.subscribe([self.topic])

        # Connection pool for database
        self._db_pool = None
        self._init_db_pool()

        logger.info(
            "MpesaKafkaConsumer initialized: brokers=%s, topic=%s, group=%s",
            self.brokers,
            self.topic,
            self.group_id,
        )

    def _init_db_pool(self) -> None:
        """Initialize database connection pool."""
        if self.postgres_dsn:
            try:
                self._db_pool = pool.SimpleConnectionPool(
                    1,
                    10,
                    dsn=self.postgres_dsn,
                    connect_timeout=5,
                )
                logger.info("Database connection pool initialized")
            except Exception as e:
                logger.error(f"Failed to initialize DB pool: {e}")

    @contextmanager
    def _get_db_connection(self) -> Iterator:
        """Context manager for database connections."""
        if not self._db_pool:
            yield None
            return

        conn = self._db_pool.getconn()
        try:
            yield conn
        except Exception as e:
            logger.error(f"Database error: {e}")
            conn.rollback()
            raise
        finally:
            self._db_pool.putconn(conn)

    def insert_raw(self, event: MpesaEvent) -> bool:
        """
        Insert raw transaction event into database.

        Args:
            event: Validated MpesaEvent

        Returns:
            True if successful, False otherwise
        """
        if not self._db_pool:
            logger.warning("Database pool not available, skipping insert")
            return False

        try:
            transaction_time = _parse_transaction_time(event.transaction_time)
            with self._get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO mpesa_transactions_raw
                          (
                            transaction_id,
                            phone_number,
                            amount,
                            account_reference,
                            transaction_time,
                            source,
                            payload
                          )
                        VALUES
                          (%s, %s, %s, %s, %s, %s, %s::jsonb)
                        ON CONFLICT (transaction_id) DO NOTHING
                        """,
                        (
                            event.transaction_id,
                            event.phone_number,
                            event.amount,
                            event.account_reference,
                            transaction_time,
                            event.source,
                            json.dumps(event.model_dump(mode="json")),
                        ),
                    )
                    conn.commit()
                    if cur.rowcount and cur.rowcount > 0:
                        logger.info("Inserted transaction: %s", event.transaction_id)
                        return True
                    logger.info("Skipped duplicate transaction: %s", event.transaction_id)
                    return False
        except Exception as e:
            logger.error(f"Failed to insert transaction: {e}")
            return False

    def consume_messages(self, max_messages: Optional[int] = None) -> int:
        """
        Consume messages from Kafka and insert into database.

        Args:
            max_messages: Maximum messages to consume (None = infinite)

        Returns:
            Number of messages consumed
        """
        count = 0

        try:
            while max_messages is None or count < max_messages:
                msg = self.consumer.poll(1.0)

                if msg is None:
                    continue

                if msg.error():
                    if "EOF" not in str(msg.error()):
                        logger.error(f"Kafka error: {msg.error()}")
                    continue

                try:
                    payload = json.loads(msg.value().decode("utf-8"))
                    payload = _coerce_legacy_event(payload)
                    event = MpesaEvent.model_validate(payload)

                    if self.insert_raw(event):
                        count += 1
                        logger.info(f"Processed event: {event.event_type} / {event.transaction_id}")
                except Exception as e:
                    logger.warning(f"Dropping invalid event: {e}")
                    continue

        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        finally:
            self.close()

        return count

    def close(self) -> None:
        """Close consumer and database connections."""
        try:
            self.consumer.close()
            logger.info("Consumer closed")
        except Exception as e:
            logger.error(f"Error closing consumer: {e}")

        if self._db_pool:
            try:
                self._db_pool.closeall()
                logger.info("Database pool closed")
            except Exception as e:
                logger.error(f"Error closing DB pool: {e}")

    def get_lag(self) -> Dict[str, int]:
        """
        Get consumer lag by partition.

        Returns:
            Dict mapping partition to lag
        """
        try:
            lag_dict = {}
            partitions = self.consumer.assignment()

            for partition in partitions:
                current_offset = self.consumer.position(partition)
                high_water_mark = self.consumer.get_watermark_offsets(partition)[1]
                lag = high_water_mark - current_offset if current_offset else 0
                lag_dict[partition.partition] = lag

            return lag_dict
        except Exception as e:
            logger.error(f"Failed to get consumer lag: {e}")
            return {}


# Backward compatibility: keep the function-based API
def run_consumer(config: ConsumerConfig, max_messages: Optional[int] = None) -> int:
    """Run consumer using function-based API (for backward compatibility)."""
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

    consumer = MpesaKafkaConsumer(
        brokers=config.brokers,
        topic=config.topic,
        group_id=config.group_id,
        postgres_dsn=config.postgres_dsn,
        batch_size=config.batch_size,
    )

    return consumer.consume_messages(max_messages=max_messages)


if __name__ == "__main__":
    cfg = ConsumerConfig(
        brokers=os.getenv("KAFKA_BROKERS", "localhost:9092"),
        topic=os.getenv("KAFKA_TOPIC_TRANSACTIONS", "mpesa-transactions"),
        group_id=os.getenv("KAFKA_GROUP_ID", "mpesa_streaming_group"),
        postgres_dsn=postgres_dsn_from_env(),
    )
    run_consumer(cfg)
