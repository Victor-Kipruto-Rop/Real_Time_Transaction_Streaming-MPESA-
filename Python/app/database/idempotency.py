"""Durable idempotency helpers for payload and transaction replay prevention."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

from sqlalchemy.exc import IntegrityError

from app.database.connection import SessionLocal
from app.database.models import IdempotencyRecord, KafkaMessageState


def _hash_payload(payload: Any) -> str:
    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def is_event_seen(event_key: str) -> bool:
    with SessionLocal() as session:
        record = session.query(IdempotencyRecord).filter_by(event_key=event_key).first()
        return record is not None


def mark_event_seen(event_key: str, transaction_id: Optional[str], payload: Any, source: str = "unknown") -> bool:
    """Create a durable record if the event did not exist. Return True when it was already seen."""
    payload_hash = _hash_payload(payload)
    with SessionLocal() as session:
        query = session.query(IdempotencyRecord).filter(IdempotencyRecord.event_key == event_key)
        if transaction_id:
            query = query.union(
                session.query(IdempotencyRecord).filter(IdempotencyRecord.transaction_id == transaction_id)
            )
        existing = query.first()
        if existing is not None:
            return True

        session.add(
            IdempotencyRecord(
                event_key=event_key,
                transaction_id=transaction_id,
                payload_hash=payload_hash,
                source=source,
                status="processed",
            )
        )
        try:
            session.commit()
            return False
        except IntegrityError:
            session.rollback()
            return True


def is_duplicate_transaction(transaction_id: str, payload: Optional[Any] = None, source: str = "unknown") -> bool:
    if not transaction_id:
        return False
    with SessionLocal() as session:
        record = session.query(IdempotencyRecord).filter_by(transaction_id=transaction_id).first()
        if record is None:
            return False
        if payload is not None:
            return record.payload_hash != _hash_payload(payload) or record.source != source
        return True


def mark_transaction_processed(transaction_id: str, payload: Any, source: str = "unknown") -> bool:
    event_key = f"txn:{transaction_id}"
    return mark_event_seen(event_key=event_key, transaction_id=transaction_id, payload=payload, source=source)


def record_message_state(
    message_key: str,
    topic: str,
    status: str,
    attempts: int = 0,
    max_attempts: int = 3,
    payload: Optional[Dict[str, Any]] = None,
    last_error: Optional[str] = None,
) -> KafkaMessageState:
    with SessionLocal() as session:
        state = session.query(KafkaMessageState).filter_by(message_key=message_key).first()
        if state is None:
            state = KafkaMessageState(
                message_key=message_key,
                topic=topic,
                status=status,
                attempts=attempts,
                max_attempts=max_attempts,
                payload=payload,
                last_error=last_error,
            )
            session.add(state)
        else:
            state.topic = topic
            state.status = status
            state.attempts = attempts
            state.max_attempts = max_attempts
            state.payload = payload
            state.last_error = last_error
        session.commit()
        session.refresh(state)
        return state


def get_message_state(message_key: str) -> Optional[KafkaMessageState]:
    with SessionLocal() as session:
        return session.query(KafkaMessageState).filter_by(message_key=message_key).first()


def mark_message_retry(message_key: str, topic: str, attempts: int, max_attempts: int = 3, payload: Optional[Dict[str, Any]] = None, last_error: Optional[str] = None) -> KafkaMessageState:
    status = "retrying" if attempts < max_attempts else "failed"
    return record_message_state(
        message_key=message_key,
        topic=topic,
        status=status,
        attempts=attempts,
        max_attempts=max_attempts,
        payload=payload,
        last_error=last_error,
    )


def record_dlq_event(message_key: str, topic: str, payload: Dict[str, Any], error_message: str, error_type: str = "unknown_error") -> KafkaMessageState:
    state = record_message_state(
        message_key=message_key,
        topic=topic,
        status="dlq",
        attempts=0,
        max_attempts=0,
        payload=payload,
        last_error=error_message,
    )
    return state
