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
