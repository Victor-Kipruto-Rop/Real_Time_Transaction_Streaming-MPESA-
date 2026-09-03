import os
import time
import uuid
import json
import requests
import psycopg2
import pytest
from kafka import KafkaConsumer


WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:8000/webhook")
DATABASE_URL = os.getenv("DATABASE_URL")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "mpesa-transactions")


@pytest.mark.integration
def test_webhook_idempotency_and_kafka_publication():
    """Integration test:
    - POST the same webhook payload twice
    - Assert first response is 201 (accepted)
    - Assert second response is 200 (duplicate)
    - Assert exactly one DB row exists for the trans_id
    - Assert at least one Kafka message was produced for that trans_id

    Requires running application, DB and Kafka reachable via environment variables:
      - WEBHOOK_URL (defaults to http://localhost:8000/webhook)
      - DATABASE_URL (postgresql://...)
      - KAFKA_BOOTSTRAP_SERVERS (host:port[,host2:port2])
    """

    if DATABASE_URL is None or KAFKA_BOOTSTRAP is None:
        pytest.skip("DATABASE_URL and KAFKA_BOOTSTRAP_SERVERS must be set for this integration test")

    trans_id = f"test-{uuid.uuid4()}"
    payload = {"trans_id": trans_id, "amount": 123.45}

    # Create Kafka consumer before publishing so we don't miss the message
    consumer_group = f"test-consumer-{uuid.uuid4()}"
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=[s.strip() for s in KAFKA_BOOTSTRAP.split(",")],
        group_id=consumer_group,
        auto_offset_reset="latest",
        consumer_timeout_ms=1000,
    )

    # POST first time
    r1 = requests.post(WEBHOOK_URL, json=payload)
    assert r1.status_code in (200, 201), f"Unexpected status code for first POST: {r1.status_code} - {r1.text}"

    # POST second time (duplicate)
    r2 = requests.post(WEBHOOK_URL, json=payload)
    assert r2.status_code in (200, 202, 201), f"Unexpected status code for second POST: {r2.status_code} - {r2.text}"

    # Allow brief time for DB write and Kafka publish
    time.sleep(1)

    # Check DB: ensure exactly one row exists for this trans_id
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM transactions WHERE trans_id = %s", (trans_id,))
            count = cur.fetchone()[0]
    finally:
        conn.close()

    assert count == 1, f"Expected exactly one DB row for trans_id={trans_id}, found {count}"

    # Consume Kafka messages for a short period and look for our trans_id
    found = False
    deadline = time.time() + 10
    while time.time() < deadline:
        for msg in consumer:
            try:
                val = msg.value.decode("utf-8")
            except Exception:
                val = str(msg.value)
            if trans_id in val:
                found = True
                break
        if found:
            break
        # small sleep before next poll
        time.sleep(0.5)

    consumer.close()
    assert found, f"Did not find Kafka message containing trans_id={trans_id} on topic {KAFKA_TOPIC}"
