"""
Kafka consumer for Project 01 (refactored with class-based API).

Consumes JSON events produced by `ingestion/webhook_receiver.py` and lands them
into Postgres (`mpesa_transactions_raw`) for downstream dbt models.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterator, Optional

from psycopg2 import pool

from schemas.transaction_schema import MpesaEvent
from prometheus_client import Counter, Gauge, start_http_server

try:
    from confluent_kafka import Consumer, KafkaException
except Exception:  # pragma: no cover
    Consumer = None  # type: ignore[assignment,misc]
    KafkaException = Exception  # type: ignore[assignment]

logger = logging.getLogger(__name__)

CONSUMER_MESSAGES_TOTAL = Counter(
    "mpesa_consumer_messages_total",
    "Kafka messages durably handled by outcome",
    ["outcome"],
)
CONSUMER_DB_FAILURES_TOTAL = Counter(
    "mpesa_consumer_database_failures_total",
    "Consumer database persistence failures",
)
CONSUMER_DLQ_TOTAL = Counter(
    "mpesa_kafka_dead_letters_total",
    "Poison Kafka messages persisted to the durable dead-letter table",
)
CONSUMER_LAG_GAUGE = Gauge(
    "mpesa_kafka_consumer_lag",
    "Estimated Kafka consumer lag by topic and partition",
    ["topic", "partition"],
)

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
        self.topic = topic or os.getenv(
            "KAFKA_TOPIC_TRANSACTIONS", "mpesa-transactions"
        )
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
                "enable.auto.commit": False,
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
            True if inserted or already present (safe to commit the Kafka offset);
            False if persistence failed (the message must not be committed).
        """
        if not self._db_pool:
            logger.warning("Database pool not available, skipping insert")
            return False

        try:
            transaction_time = _parse_transaction_time(event.transaction_time)
            event_payload = event.model_dump(mode="json")
            event_key = event.event_key or hashlib.sha256(
                json.dumps(event_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            with self._get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO mpesa_callback_events
                          (event_key, event_type, source, payload)
                        VALUES (%s, %s, %s, %s::json)
                        ON CONFLICT (event_key) DO NOTHING
                        """,
                        (
                            event_key,
                            event.event_type,
                            event.source,
                            json.dumps(event_payload),
                        ),
                    )

                    # Every callback family is retained for audit. C2B validation
                    # is a pre-transaction decision, not proof of a received payment;
                    # only a C2B confirmation may update the transaction ledger table.
                    if event.event_type != "c2b_confirmation":
                        conn.commit()
                        logger.info("Persisted callback audit event: %s", event.event_type)
                        return True

                    if not event.transaction_id:
                        raise ValueError("C2B confirmation is missing transaction_id")

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
                        ON CONFLICT (transaction_id) DO UPDATE SET
                          phone_number = COALESCE(EXCLUDED.phone_number, mpesa_transactions_raw.phone_number),
                          amount = COALESCE(EXCLUDED.amount, mpesa_transactions_raw.amount),
                          account_reference = COALESCE(EXCLUDED.account_reference, mpesa_transactions_raw.account_reference),
                          transaction_time = COALESCE(EXCLUDED.transaction_time, mpesa_transactions_raw.transaction_time),
                          source = EXCLUDED.source,
                          payload = EXCLUDED.payload,
                          processed_at = CURRENT_TIMESTAMP
                        """,
                        (
                            event.transaction_id,
                            event.phone_number,
                            event.amount,
                            event.account_reference,
                            transaction_time.isoformat() if transaction_time else None,
                            event.source,
                            json.dumps(event.model_dump(mode="json")),
                        ),
                    )
                    conn.commit()
                    if cur.rowcount and cur.rowcount > 0:
                        logger.info("Inserted transaction: %s", event.transaction_id)
                        return True
                    logger.info(
                        "Skipped duplicate transaction: %s", event.transaction_id
                    )
                    # A duplicate is already durably represented, so it is safe
                    # to commit this Kafka offset.
                    return True
        except Exception as e:
            CONSUMER_DB_FAILURES_TOTAL.inc()
            logger.error("Failed to insert transaction: %s", e)
            return False

    def _persist_dead_letter(self, msg: Any, error: Exception) -> bool:
        """Persist a poison message before committing its Kafka offset."""
        if not self._db_pool:
            return False
        try:
            raw = msg.value()
            raw_text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
            key_value = msg.key()
            key_text = key_value.decode("utf-8", errors="replace") if isinstance(key_value, bytes) else (str(key_value) if key_value is not None else None)
            with self._get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO kafka_dead_letters
                          (topic, partition_id, message_offset, message_key, raw_value, error_type, error_message, attempts, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 1, 'pending')
                        ON CONFLICT (topic, partition_id, message_offset) DO NOTHING
                        """,
                        (
                            msg.topic(),
                            msg.partition(),
                            msg.offset(),
                            key_text,
                            raw_text,
                            type(error).__name__,
                            str(error)[:4000],
                        ),
                    )
                conn.commit()
            CONSUMER_DLQ_TOTAL.inc()
            return True
        except Exception:
            CONSUMER_DB_FAILURES_TOTAL.inc()
            logger.exception("Failed to persist Kafka dead-letter record")
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

                    if not self.insert_raw(event):
                        # Do not advance the partition offset after a persistence
                        # failure; a restart can safely retry this message.
                        logger.error(
                            "Stopping consumption without committing offset after persistence failure"
                        )
                        break

                    self.consumer.commit(message=msg, asynchronous=False)
                    CONSUMER_MESSAGES_TOTAL.labels(outcome="handled").inc()
                    count += 1
                    logger.info(
                        "Handled event: %s / %s",
                        event.event_type,
                        event.transaction_id,
                    )
                except Exception as e:
                    # Poison messages are moved to a durable PostgreSQL DLQ first.
                    # Commit only after that write succeeds; if PostgreSQL is down,
                    # leave the Kafka offset uncommitted so the record can retry.
                    logger.error("Invalid event; attempting durable DLQ: %s", e)
                    if not self._persist_dead_letter(msg, e):
                        logger.error("DLQ persistence failed; retaining Kafka offset")
                        break
                    self.consumer.commit(message=msg, asynchronous=False)
                    CONSUMER_MESSAGES_TOTAL.labels(outcome="dead_lettered").inc()
                    count += 1

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
                positions = self.consumer.position([partition])
                current_offset = positions[0].offset if positions else -1
                high_water_mark = self.consumer.get_watermark_offsets(partition)[1]
                lag = max(0, high_water_mark - current_offset) if current_offset >= 0 else 0
                lag_dict[partition.partition] = lag
                CONSUMER_LAG_GAUGE.labels(
                    topic=self.topic, partition=str(partition.partition)
                ).set(lag)

            return lag_dict
        except Exception as e:
            logger.error(f"Failed to get consumer lag: {e}")
            return {}


class KafkaConsumerClient:
    """Backward-compatible kafka-python consumer client used by legacy tests."""

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic: str = "mpesa-transactions",
        group_id: str = "mpesa_consumer_group",
    ):
        from kafka import KafkaConsumer  # Local import to keep optional dependency behavior

        self._consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )

    def consume(self, max_messages: Optional[int] = None):
        count = 0
        for message in self._consumer:
            if max_messages is not None and count >= max_messages:
                break
            payload = message.value
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8")
            yield json.loads(payload)
            count += 1

    def commit(self) -> None:
        self._consumer.commit()

    def close(self) -> None:
        self._consumer.close()


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
    metrics_port = int(os.getenv("KAFKA_CONSUMER_METRICS_PORT", "8080"))
    start_http_server(metrics_port)
    logger.info("Prometheus metrics server listening on port %s", metrics_port)
    cfg = ConsumerConfig(
        brokers=os.getenv("KAFKA_BROKERS", "localhost:9092"),
        topic=os.getenv("KAFKA_TOPIC_TRANSACTIONS", "mpesa-transactions"),
        group_id=os.getenv("KAFKA_GROUP_ID", "mpesa_streaming_group"),
        postgres_dsn=postgres_dsn_from_env(),
    )
    run_consumer(cfg)
