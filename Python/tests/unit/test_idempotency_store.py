import json
import os
import uuid
from unittest.mock import MagicMock

from sqlalchemy import text

os.environ.setdefault("USE_SQLITE_FOR_TESTS", "1")

from app.database.connection import engine, init_db
from app.database.idempotency import (
    get_message_state,
    is_duplicate_transaction,
    mark_message_retry,
    mark_transaction_processed,
    record_message_state,
)
from ingestion import kafka_consumer
from ingestion.kafka_consumer import SafaricomTransactionProcessor
from ingestion.kafka_producer import MpesaKafkaProducer


def test_transaction_idempotency_is_persisted():
    init_db()
    transaction_id = f"TXN-DB-{uuid.uuid4()}"
    payload = {"TransID": transaction_id, "MSISDN": "254712345678", "TransAmount": "1000"}

    assert mark_transaction_processed(transaction_id, payload, source="webhook") is False
    assert is_duplicate_transaction(transaction_id, payload, source="webhook") is False
    assert mark_transaction_processed(transaction_id, payload, source="webhook") is True
    assert is_duplicate_transaction(transaction_id, payload, source="webhook") is False


def test_ensure_transaction_id_unique_index_deduplicates_existing_rows():
    init_db()
    with engine.begin() as conn:
        conn.execute(text("DROP INDEX IF EXISTS uq_mpesa_transactions_raw_transaction_id"))
        conn.execute(
            text(
                """
                DELETE FROM mpesa_transactions_raw
                WHERE transaction_id IN ('TXN-DUP-DEDUP-1', 'TXN-DUP-DEDUP-2')
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO mpesa_transactions_raw (
                    transaction_id, phone_number, amount, transaction_time,
                    transaction_status, payment_method, reference,
                    account_reference, merchant_id, region, processed_at, raw_data
                ) VALUES
                    ('TXN-DUP-DEDUP-1', '254712345678', 1000, '20260613120000', 'completed', 'c2b', 'REF1', 'ACC1', '174379', 'Nairobi', '2026-06-13T12:00:00', '{\"TransID\":\"TXN-DUP-DEDUP-1\"}'),
                    ('TXN-DUP-DEDUP-1', '254712345678', 1000, '20260613120000', 'completed', 'c2b', 'REF1', 'ACC1', '174379', 'Nairobi', '2026-06-13T12:00:00', '{\"TransID\":\"TXN-DUP-DEDUP-1\"}')
                """
            )
        )

    from app.database.connection import ensure_transaction_id_unique_index

    ensure_transaction_id_unique_index()

    with engine.connect() as conn:
        remaining = conn.execute(
            text("SELECT COUNT(*) FROM mpesa_transactions_raw WHERE transaction_id = 'TXN-DUP-DEDUP-1'")
        ).scalar_one()
        assert remaining == 1


def test_kafka_message_state_tracks_retries_and_failures():
    init_db()
    message_key = f"msg-{uuid.uuid4()}"

    state = record_message_state(
        message_key=message_key,
        topic="mpesa-transactions",
        status="queued",
        attempts=1,
        max_attempts=3,
        payload={"TransID": f"TXN-{uuid.uuid4()}"},
    )

    assert state.status == "queued"
    retry_state = mark_message_retry(
        message_key=message_key,
        topic="mpesa-transactions",
        attempts=2,
        max_attempts=3,
        payload={"TransID": f"TXN-{uuid.uuid4()}"},
        last_error="temporary error",
    )

    assert retry_state.status == "retrying"
    assert retry_state.attempts == 2
    persisted = get_message_state(message_key)
    assert persisted is not None
    assert persisted.last_error == "temporary error"


def test_retry_state_accumulates_across_repeated_failures():
    init_db()
    message_key = f"msg-{uuid.uuid4()}"

    first = mark_message_retry(
        message_key=message_key,
        topic="mpesa-transactions",
        attempts=1,
        max_attempts=3,
        payload={"TransID": f"TXN-{uuid.uuid4()}"},
        last_error="temporary error",
    )
    second = mark_message_retry(
        message_key=message_key,
        topic="mpesa-transactions",
        attempts=2,
        max_attempts=3,
        payload={"TransID": f"TXN-{uuid.uuid4()}"},
        last_error="still failing",
    )

    assert first.status == "retrying"
    assert second.status == "retrying"
    assert second.attempts == 2

    persisted = get_message_state(message_key)
    assert persisted is not None
    assert persisted.last_error == "still failing"


def test_consumer_retry_state_tracks_attempts_per_message(monkeypatch):
    processor = SafaricomTransactionProcessor.__new__(SafaricomTransactionProcessor)
    processor.kafka_config = {"topic": "mpesa-transactions"}
    processor.max_retries = 3
    processor.retry_backoff_seconds = 0
    processor.error_count = 0
    processor._message_attempts = {}

    message = {
        "TransID": f"TXN-RETRY-{uuid.uuid4()}",
        "MSISDN": "254712345678",
        "TransAmount": "1000",
        "TransTime": "20240601120000",
    }

    retry_state = MagicMock(status="retrying", attempts=1)
    dlq_state = MagicMock(status="dlq")
    monkeypatch.setattr(kafka_consumer, "mark_message_retry", lambda **kwargs: retry_state)
    monkeypatch.setattr(kafka_consumer, "record_dlq_event", lambda **kwargs: dlq_state)

    processor._handle_processing_error(message, ValueError("temporary failure"), 0)
    processor._handle_processing_error(message, ValueError("still failing"), 1)

    assert processor._message_attempts[processor._message_key_for(message)] == 2


def test_producer_rejects_duplicate_transaction_ids_before_publish():
    producer = MpesaKafkaProducer.__new__(MpesaKafkaProducer)
    producer.bootstrap_servers = "localhost:9092"
    producer.topic = "mpesa-transactions"
    producer.dlq_topic = "mpesa-transactions-dlq"
    producer.retry_topic = "mpesa-transactions-retry"
    producer.max_retries = 3
    producer.retry_backoff_seconds = 0
    producer._seen_transaction_ids = set()
    producer._seen_lock = MagicMock()
    producer._producer = MagicMock()

    transaction = {
        "TransID": f"TXN-DUP-{uuid.uuid4()}",
        "MSISDN": "254712345678",
        "TransAmount": "1000",
        "TransTime": "20240601120000",
    }

    producer._producer.produce = MagicMock()
    producer._producer.poll = MagicMock()
    producer._producer.flush = MagicMock()

    assert producer.publish_transaction(transaction) is True
    assert producer.publish_transaction(transaction) is False


def test_insert_transaction_counts_only_real_database_inserts():
    processor = SafaricomTransactionProcessor.__new__(SafaricomTransactionProcessor)
    processor.db_connection = MagicMock()
    processor.processed_count = 0
    processor.error_count = 0
    processor._message_attempts = {}

    cursor = MagicMock()
    cursor.execute.return_value = None
    cursor.rowcount = 0
    processor.db_connection.cursor.return_value = cursor

    transaction = {
        "transaction_id": f"TXN-CONFLICT-{uuid.uuid4()}",
        "phone_number": "254712345678",
        "amount": 1000,
        "business_shortcode": "174379",
        "transaction_time": "20260613120000",
        "transaction_status": "completed",
        "payment_method": "c2b",
        "reference": "REF-1",
        "account_reference": "ACC-1",
        "merchant_id": "174379",
        "region": "Nairobi",
        "processed_at": "2026-06-13T12:00:00",
        "raw_data": '{"TransID":"TXN-CONFLICT"}',
    }

    assert processor.insert_transaction(transaction) is False
    assert processor.processed_count == 0


def test_batch_insert_transactions_counts_only_inserted_rows():
    processor = SafaricomTransactionProcessor.__new__(SafaricomTransactionProcessor)
    processor.db_connection = MagicMock()
    processor.processed_count = 0
    processor.error_count = 0

    cursor = MagicMock()
    cursor.rowcount = 2
    processor.db_connection.cursor.return_value = cursor

    transactions = [
        {"transaction_id": f"TXN-BATCH-{i}", "phone_number": "254712345678", "amount": 1000, "business_shortcode": "174379", "transaction_time": "20260613120000", "transaction_status": "completed", "payment_method": "c2b", "reference": f"REF-{i}", "account_reference": f"ACC-{i}", "merchant_id": "174379", "region": "Nairobi", "processed_at": "2026-06-13T12:00:00", "raw_data": '{"TransID":"TXN-BATCH"}'}
        for i in range(3)
    ]

    assert processor.batch_insert_transactions(transactions) is True
    assert processor.processed_count == 2
