"""Transactional database outbox for reliable webhook-to-Kafka delivery.

The HTTP handler only acknowledges a callback after its event has been committed to
PostgreSQL. A separate relay publishes pending rows and marks them published after
Kafka confirms delivery. Delivery is at-least-once; consumers must remain idempotent.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.database.connection import SessionLocal
from app.database.models import OutboxEvent
from ingestion.event_identity import replay_key

logger = logging.getLogger(__name__)


def enqueue_callback(event_type: str, payload: Dict[str, Any], topic: Optional[str] = None) -> Tuple[str, bool]:
    """Persist a callback event once. Return its stable key and whether it was inserted."""
    key = replay_key(payload, event_type)
    result = payload.get("Result") if isinstance(payload.get("Result"), dict) else {}
    body = payload.get("Body") if isinstance(payload.get("Body"), dict) else {}
    stk = body.get("stkCallback") if isinstance(body.get("stkCallback"), dict) else {}
    amount = payload.get("TransAmount")
    if amount is None and isinstance(stk.get("CallbackMetadata"), dict):
        items = stk["CallbackMetadata"].get("Item", [])
        if isinstance(items, list):
            amount_item = next((item for item in items if isinstance(item, dict) and item.get("Name") == "Amount"), None)
            amount = amount_item.get("Value") if amount_item else None
    transaction_id = (
        payload.get("TransID")
        or result.get("TransactionID")
        or result.get("ConversationID")
        or stk.get("CheckoutRequestID")
        or stk.get("MerchantRequestID")
    )
    envelope = {
        "event_key": key,
        "event_type": event_type,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "source": "daraja_webhook",
        "transaction_id": str(transaction_id) if transaction_id else None,
        "phone_number": payload.get("MSISDN"),
        "amount": str(amount) if amount is not None else None,
        "account_reference": payload.get("AccountReference") or payload.get("BillRefNumber"),
        "transaction_time": payload.get("TransTime"),
        "data": payload,
    }
    target_topic = topic or os.getenv("KAFKA_TOPIC_TRANSACTIONS", "mpesa-transactions")
    with SessionLocal() as session:
        existing = session.execute(
            select(OutboxEvent.id).where(OutboxEvent.event_key == key)
        ).first()
        if existing:
            return key, False
        session.add(
            OutboxEvent(
                event_key=key,
                event_type=event_type,
                topic=target_topic,
                payload=envelope,
                status="pending",
                attempts=0,
            )
        )
        try:
            session.commit()
            return key, True
        except IntegrityError:
            session.rollback()
            # A concurrent request may have inserted the same event key.
            existing = session.execute(
                select(OutboxEvent.id).where(OutboxEvent.event_key == key)
            ).first()
            if existing:
                return key, False
            raise


def _claim_one(lease_seconds: int = 60) -> Optional[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        stmt = (
            select(OutboxEvent)
            .where(
                or_(
                    OutboxEvent.status == "pending",
                    (OutboxEvent.status == "publishing") & (OutboxEvent.lease_until < now),
                ),
                # Avoid hot-looping a failed row until its backoff has elapsed.
                OutboxEvent.next_attempt_at <= now,
            )
            .order_by(OutboxEvent.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        row = session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        row.status = "publishing"
        row.lease_until = now + timedelta(seconds=lease_seconds)
        row.attempts += 1
        session.commit()
        return {
            "id": row.id,
            "event_key": row.event_key,
            "event_type": row.event_type,
            "topic": row.topic,
            "payload": row.payload,
            "attempts": row.attempts,
        }


def _mark_published(row_id: int) -> None:
    with SessionLocal() as session:
        row = session.get(OutboxEvent, row_id)
        if row is None:
            return
        row.status = "published"
        row.published_at = datetime.now(timezone.utc)
        row.lease_until = None
        row.last_error = None
        session.commit()


def _mark_retry(row_id: int, error: str, attempts: int) -> None:
    # Bounded exponential backoff; row remains durable and retryable indefinitely.
    delay = min(300, 2 ** min(max(attempts, 1), 8))
    with SessionLocal() as session:
        row = session.get(OutboxEvent, row_id)
        if row is None:
            return
        row.status = "pending"
        row.lease_until = None
        row.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
        row.last_error = error[:4000]
        session.commit()


def relay_once(producer: Any) -> bool:
    """Publish one outbox row. Returns False when there is no eligible work."""
    row = _claim_one()
    if row is None:
        return False
    try:
        # The producer callback must confirm broker delivery, not just local enqueue.
        delivered = producer.publish_event(row["payload"], topic=row["topic"], key=row["event_key"])
        if not delivered:
            raise RuntimeError("Kafka producer did not confirm delivery")
        _mark_published(row["id"])
        logger.info("Outbox event published", extra={"event_key": row["event_key"], "topic": row["topic"]})
    except Exception as exc:
        _mark_retry(row["id"], str(exc), row["attempts"])
        logger.exception("Outbox delivery failed; event retained for retry", extra={"event_key": row["event_key"]})
    return True


def run_forever() -> None:
    """Run the outbox relay as a dedicated process."""
    from ingestion.kafka_producer import MpesaKafkaProducer

    producer = MpesaKafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_BROKERS", "localhost:9092"),
        topic=os.getenv("KAFKA_TOPIC_TRANSACTIONS", "mpesa-transactions"),
    )
    idle_seconds = float(os.getenv("OUTBOX_IDLE_SECONDS", "1"))
    try:
        while True:
            if not relay_once(producer):
                time.sleep(idle_seconds)
    finally:
        close = getattr(producer, "close", None)
        if callable(close):
            close()


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    run_forever()
