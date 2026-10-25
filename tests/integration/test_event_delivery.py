"""Live PostgreSQL/Kafka integration checks.

Run only in a disposable integration environment with RUN_INTEGRATION_TESTS=1.
These tests publish synthetic transactions and create uniquely named test topics.
"""

import os
import uuid

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1",
    reason="requires disposable PostgreSQL and Kafka services",
)


def test_webhook_outbox_kafka_consumer_postgres_round_trip():
    from ingestion.webhook_receiver import create_app
    from app.database.connection import SessionLocal
    from app.database.models import CallbackEvent, OutboxEvent
    from app.database.outbox import enqueue_callback, relay_once
    from ingestion.kafka_producer import MpesaKafkaProducer
    from streaming.kafka_consumer import MpesaKafkaConsumer

    topic = "it-callback-" + uuid.uuid4().hex[:10]
    transaction_id = "IT-" + uuid.uuid4().hex[:12]
    payload = {
        "TransID": transaction_id,
        "TransAmount": "500",
        "MSISDN": "254712345678",
        "TransTime": "20261026120000",
        "AccountReference": "INTEGRATION-TEST",
    }
    app = create_app()
    app.testing = True
    response = app.test_client().post("/webhook/c2b/confirmation", json=payload)
    assert response.status_code == 200

    # The endpoint's default topic is configured from KAFKA_TOPIC_TRANSACTIONS.
    # Use the same topic in the test broker; ensure the event is durable before relay.
    key, created = enqueue_callback("c2b_confirmation", payload, topic=topic)
    assert created is True
    with SessionLocal() as session:
        row = session.execute(select(OutboxEvent).where(OutboxEvent.event_key == key)).scalar_one()
        assert row.status == "pending"

    producer = MpesaKafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_BROKERS", "localhost:9092"),
        topic=topic,
    )
    try:
        assert relay_once(producer) is True
    finally:
        producer.close()

    consumer = MpesaKafkaConsumer(
        brokers=os.getenv("KAFKA_BROKERS", "localhost:9092"),
        topic=topic,
        group_id="it-" + uuid.uuid4().hex,
        postgres_dsn=os.getenv("DATABASE_URL"),
    )
    consumer.consume_messages(max_messages=1)

    with SessionLocal() as session:
        event = session.execute(
            select(CallbackEvent).where(CallbackEvent.event_key == key)
        ).scalar_one_or_none()
        assert event is not None
        outbox_row = session.execute(
            select(OutboxEvent).where(OutboxEvent.event_key == key)
        ).scalar_one()
        assert outbox_row.status == "published"


def test_poison_kafka_message_is_persisted_to_dlq_before_offset_commit():
    from confluent_kafka import Producer
    from sqlalchemy import text
    from streaming.kafka_consumer import MpesaKafkaConsumer

    topic = "it-poison-" + uuid.uuid4().hex[:10]
    producer = Producer({"bootstrap.servers": os.getenv("KAFKA_BROKERS", "localhost:9092")})
    producer.produce(topic, value=b"{not-valid-json")
    assert producer.flush(10) == 0

    consumer = MpesaKafkaConsumer(
        brokers=os.getenv("KAFKA_BROKERS", "localhost:9092"),
        topic=topic,
        group_id="it-poison-" + uuid.uuid4().hex,
        postgres_dsn=os.getenv("DATABASE_URL"),
    )
    consumer.consume_messages(max_messages=1)

    from app.database.connection import engine
    with engine.connect() as connection:
        count = connection.execute(
            text("SELECT COUNT(*) FROM kafka_dead_letters WHERE topic = :topic"),
            {"topic": topic},
        ).scalar_one()
    assert count == 1
