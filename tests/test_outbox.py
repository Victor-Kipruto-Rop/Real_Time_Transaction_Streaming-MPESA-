"""Outbox behavior tests with an isolated SQLite database."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.connection import Base
from app.database import models  # noqa: F401
from app.database import outbox


def _isolated_outbox(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(outbox, "SessionLocal", sessions)
    return engine, sessions


def test_callback_enqueue_is_durable_and_idempotent(monkeypatch):
    engine, sessions = _isolated_outbox(monkeypatch)
    payload = {
        "TransID": "TX-OUTBOX-1",
        "TransAmount": "500",
        "MSISDN": "254712345678",
        "TransTime": "20261026120000",
    }

    first_key, first_created = outbox.enqueue_callback("c2b_confirmation", payload)
    # Same provider receipt with conflicting amount must not replace the durable
    # first-seen event; the conflicting delivery requires investigation.
    conflicting_payload = {**payload, "TransAmount": "999"}
    second_key, second_created = outbox.enqueue_callback(
        "c2b_confirmation", conflicting_payload
    )

    assert first_key == second_key
    assert first_created is True
    assert second_created is False
    with sessions() as session:
        rows = session.execute(select(models.OutboxEvent)).scalars().all()
        assert len(rows) == 1
        assert rows[0].status == "pending"
        assert rows[0].payload["transaction_id"] == "TX-OUTBOX-1"
        assert rows[0].payload["amount"] == "500"
    engine.dispose()


def test_relay_marks_published_only_after_confirmed_delivery(monkeypatch):
    monkeypatch.setattr(outbox, "_claim_one", lambda: {
        "id": 7, "event_key": "key", "event_type": "c2b_confirmation",
        "topic": "topic", "payload": {"event_type": "c2b_confirmation"}, "attempts": 1,
    })
    published = []
    retried = []
    monkeypatch.setattr(outbox, "_mark_published", published.append)
    monkeypatch.setattr(outbox, "_mark_retry", lambda row_id, error, attempts: retried.append((row_id, error, attempts)))

    class Producer:
        def publish_event(self, *args, **kwargs):
            return False

    assert outbox.relay_once(Producer()) is True
    assert published == []
    assert retried and retried[0][0] == 7


def test_relay_marks_row_published_after_delivery_confirmation(monkeypatch):
    monkeypatch.setattr(outbox, "_claim_one", lambda: {
        "id": 8, "event_key": "key2", "event_type": "stk_callback",
        "topic": "topic", "payload": {"event_type": "stk_callback"}, "attempts": 1,
    })
    published = []
    retried = []
    monkeypatch.setattr(outbox, "_mark_published", published.append)
    monkeypatch.setattr(outbox, "_mark_retry", lambda *args: retried.append(args))

    class Producer:
        def publish_event(self, *args, **kwargs):
            return True

    assert outbox.relay_once(Producer()) is True
    assert published == [8]
    assert retried == []



def test_retry_records_backoff_and_keeps_event_durable(monkeypatch):
    from datetime import datetime, timezone
    from app.database.models import OutboxEvent

    engine, sessions = _isolated_outbox(monkeypatch)
    with sessions() as session:
        row = OutboxEvent(
            event_key="retry-key",
            event_type="c2b_confirmation",
            topic="retry-topic",
            payload={"event_key": "retry-key"},
            status="publishing",
            attempts=3,
        )
        session.add(row)
        session.commit()
        row_id = row.id

    before = datetime.now(timezone.utc)
    outbox._mark_retry(row_id, "synthetic broker unavailable", attempts=3)
    with sessions() as session:
        row = session.get(OutboxEvent, row_id)
        assert row is not None
        assert row.status == "pending"
        assert row.lease_until is None
        assert row.next_attempt_at > before
        assert row.last_error == "synthetic broker unavailable"
        assert row.attempts == 3
    engine.dispose()


def test_retry_error_storage_is_bounded(monkeypatch):
    from app.database.models import OutboxEvent

    engine, sessions = _isolated_outbox(monkeypatch)
    with sessions() as session:
        row = OutboxEvent(
            event_key="retry-bounded-key",
            event_type="c2b_confirmation",
            topic="retry-topic",
            payload={"event_key": "retry-bounded-key"},
            status="publishing",
            attempts=1,
        )
        session.add(row)
        session.commit()
        row_id = row.id

    outbox._mark_retry(row_id, "x" * 5000, attempts=1)
    with sessions() as session:
        row = session.get(OutboxEvent, row_id)
        assert row is not None
        assert len(row.last_error) == 4000
        assert row.status == "pending"
    engine.dispose()
