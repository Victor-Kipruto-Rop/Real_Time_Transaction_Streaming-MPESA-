import json
import os
import uuid

os.environ.setdefault("USE_SQLITE_FOR_TESTS", "1")

from app.database.connection import init_db
from app.database.idempotency import (
    get_message_state,
    is_duplicate_transaction,
    mark_message_retry,
    mark_transaction_processed,
    record_message_state,
)


def test_transaction_idempotency_is_persisted():
    init_db()
    transaction_id = f"TXN-DB-{uuid.uuid4()}"
    payload = {"TransID": transaction_id, "MSISDN": "254712345678", "TransAmount": "1000"}

    assert mark_transaction_processed(transaction_id, payload, source="webhook") is False
    assert is_duplicate_transaction(transaction_id, payload, source="webhook") is False
    assert mark_transaction_processed(transaction_id, payload, source="webhook") is True
    assert is_duplicate_transaction(transaction_id, payload, source="webhook") is False


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
