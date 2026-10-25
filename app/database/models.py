"""SQLAlchemy models for durable idempotency and operational telemetry."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import JSON, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IdempotencyRecord(Base):
    """Persisted idempotency-tracking record for duplicate payload prevention."""

    __tablename__ = "idempotency_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    transaction_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    payload_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="processed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    __table_args__ = (
        UniqueConstraint("event_key", name="uq_idempotency_event_key"),
        UniqueConstraint("transaction_id", name="uq_idempotency_transaction_id"),
    )


class KafkaMessageState(Base):
    """Track Kafka message lifecycle with retry and DLQ state."""

    __tablename__ = "kafka_message_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    topic: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class ErrorLog(Base):
    """Operational error record used by DLQ and monitoring components."""

    __tablename__ = "error_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    error_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_stacktrace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recovery_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    payload_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class OutboxEvent(Base):
    """Durable callback event waiting for Kafka delivery."""

    __tablename__ = "event_outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    topic: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lease_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

class CallbackEvent(Base):
    """Durable audit record for every accepted callback family."""

    __tablename__ = "mpesa_callback_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    topic: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    partition_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    message_offset: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class KafkaDeadLetter(Base):
    """Durable poison-message record; offsets are committed only after this write."""

    __tablename__ = "kafka_dead_letters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String(128), nullable=False)
    partition_id: Mapped[int] = mapped_column(Integer, nullable=False)
    message_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    message_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    raw_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_type: Mapped[str] = mapped_column(String(128), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (UniqueConstraint("topic", "partition_id", "message_offset", name="uq_kafka_dead_letter_offset"),)
