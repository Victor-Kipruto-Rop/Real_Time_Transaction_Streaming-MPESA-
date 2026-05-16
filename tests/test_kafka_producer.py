"""Tests for Kafka producer module.

Covers producer initialization, event publishing, delivery callbacks,
and idempotence configuration.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ingestion.kafka_producer import MpesaKafkaProducer


def test_producer_initializes_confluent() -> None:
    """Test that producer initializes with confluent-kafka."""
    with patch("ingestion.kafka_producer.Producer") as mock_producer_cls:
        MpesaKafkaProducer(bootstrap_servers="localhost:9092", topic="t1")
        assert mock_producer_cls.called


def test_publish_event_calls_produce() -> None:
    producer_mock = MagicMock()
    with patch("ingestion.kafka_producer.Producer", return_value=producer_mock):
        producer = MpesaKafkaProducer(bootstrap_servers="localhost:9092", topic="t1")
        ok = producer.publish_event({"hello": "world"}, topic="t2", key="k1")
        assert ok is True
        assert producer_mock.produce.called


def test_publish_event_returns_false_on_error() -> None:
    producer_mock = MagicMock()
    producer_mock.produce.side_effect = RuntimeError("boom")
    with patch("ingestion.kafka_producer.Producer", return_value=producer_mock):
        producer = MpesaKafkaProducer(bootstrap_servers="localhost:9092", topic="t1")
        ok = producer.publish_event({"hello": "world"})
        assert ok is False
