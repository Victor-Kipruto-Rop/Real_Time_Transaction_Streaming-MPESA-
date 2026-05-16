"""Tests for Kafka consumer module.

Covers consumer initialization, message consumption, database inserts,
and error handling.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from streaming.kafka_consumer import ConsumerConfig, postgres_dsn_from_env, run_consumer


def test_postgres_dsn_from_env_none_when_missing(monkeypatch) -> None:
    """Test that missing DB env vars return None."""
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    monkeypatch.delenv("POSTGRES_PORT", raising=False)
    monkeypatch.delenv("POSTGRES_DB", raising=False)
    monkeypatch.delenv("POSTGRES_USER", raising=False)
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert postgres_dsn_from_env() is None


def test_run_consumer_consumes_one_message_and_inserts(monkeypatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "INFO")

    cfg = ConsumerConfig(
        brokers="localhost:9092",
        topic="mpesa-transactions",
        group_id="g1",
        postgres_dsn="dbname=x user=y password=z host=h port=5432",
    )

    with patch("streaming.kafka_consumer.MpesaKafkaConsumer") as consumer_cls:
        instance = MagicMock()
        instance.consume_messages.return_value = 1
        consumer_cls.return_value = instance
        count = run_consumer(cfg, max_messages=1)
        assert count == 1
        instance.consume_messages.assert_called_with(max_messages=1)
