"""
Kafka consumer for Project 01.

Consumes JSON events produced by `ingestion/webhook_receiver.py` and lands them
into Postgres (`mpesa_transactions_raw`) for downstream dbt models.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Optional

import psycopg2

from schemas.transaction_schema import MpesaEvent

try:
    from confluent_kafka import Consumer, KafkaException
except Exception:  # pragma: no cover
    Consumer = None  # type: ignore[assignment,misc]
    KafkaException = Exception  # type: ignore[assignment]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConsumerConfig:
    brokers: str
    topic: str
    group_id: str
    postgres_dsn: Optional[str]


def postgres_dsn_from_env() -> Optional[str]:
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


def insert_raw(conn, event: MpesaEvent) -> None:
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
            """,
            (
                event.transaction_id,
                event.phone_number,
                event.amount,
                event.account_reference,
                event.transaction_time,
                event.source,
                json.dumps(event.model_dump(mode="json")),
            ),
        )
    conn.commit()


def run_consumer(config: ConsumerConfig, max_messages: Optional[int] = None) -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

    if Consumer is None:
        raise RuntimeError(
            "confluent-kafka is not installed. Install `requirements.txt` for Project 01."
        )

    consumer = Consumer(
        {
            "bootstrap.servers": config.brokers,
            "group.id": config.group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        }
    )
    consumer.subscribe([config.topic])

    conn = None
    if config.postgres_dsn:
        conn = psycopg2.connect(config.postgres_dsn)

    logger.info("Consumer started topic=%s group_id=%s", config.topic, config.group_id)

    consumed = 0

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                raise KafkaException(msg.error())

            try:
                payload = json.loads(msg.value().decode("utf-8"))
                event = MpesaEvent.model_validate(payload)
            except Exception as e:
                logger.warning("Dropping invalid event: %s", str(e))
                continue

            logger.info(
                "Consumed event_type=%s transaction_id=%s", event.event_type, event.transaction_id
            )

            if conn:
                insert_raw(conn, event)

            consumed += 1
            if max_messages is not None and consumed >= max_messages:
                return
    finally:
        try:
            consumer.close()
        except Exception:
            pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass


if __name__ == "__main__":
    cfg = ConsumerConfig(
        brokers=os.getenv("KAFKA_BROKERS", "localhost:9092"),
        topic=os.getenv("KAFKA_TOPIC_TRANSACTIONS", "mpesa-transactions"),
        group_id=os.getenv("KAFKA_GROUP_ID", "mpesa_streaming_group"),
        postgres_dsn=postgres_dsn_from_env(),
    )
    run_consumer(cfg)
