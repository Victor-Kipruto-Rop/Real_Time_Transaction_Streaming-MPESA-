"""
Kafka Producer for M-Pesa transaction streaming.

Publishes transaction events to Kafka topics for real-time processing
by downstream consumers (stream processors, analytics, notifications).
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)

try:
    from confluent_kafka import Producer
except Exception:  # pragma: no cover
    Producer = None  # type: ignore[assignment,misc]


class MpesaKafkaProducer:
    """
    Producer for publishing M-Pesa transactions to Kafka.

    Attributes:
        bootstrap_servers (str): Kafka broker addresses
        topic (str): Default Kafka topic for transactions
        producer (KafkaProducer): Kafka producer instance
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic: str = "mpesa-transactions",
    ):
        """
        Initialize Kafka producer.

        Args:
            bootstrap_servers: Comma-separated list of Kafka brokers
            topic: Default topic for publishing transactions
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic

        if Producer is None:
            raise RuntimeError(
                "confluent-kafka is not installed. Install `requirements.txt` for Project 01."
            )

        self._producer = Producer(
            {
                "bootstrap.servers": bootstrap_servers,
                "acks": "all",
                "retries": 3,
                "enable.idempotence": True,
            }
        )
        logger.info("Kafka producer initialized with brokers: %s", bootstrap_servers)

    def _delivery_report(self, err, msg) -> None:
        if err is not None:
            logger.error("Delivery failed: %s", err)
        else:
            logger.info(
                "Delivered to %s [%s] @ offset %s",
                msg.topic(),
                msg.partition(),
                msg.offset(),
            )

    def publish_event(
        self,
        event: Union[Dict[str, Any], Any],
        topic: Optional[str] = None,
        key: Optional[str] = None,
    ) -> bool:
        """
        Publish a pre-built event to Kafka.

        Args:
            event: Dict-like event payload
            topic: Optional topic override
            key: Optional partition key
        """
        target_topic = topic or self.topic

        try:
            payload = (
                event.model_dump(mode="json") if hasattr(event, "model_dump") else event
            )
            self._producer.produce(
                target_topic,
                value=json.dumps(payload).encode("utf-8"),
                key=key.encode("utf-8") if key else None,
                on_delivery=self._delivery_report,
            )
            self._producer.poll(0)
            self._producer.flush(5)
            return True
        except Exception as e:
            logger.error("Error publishing event: %s", str(e))
            return False

    def publish_transaction(
        self,
        transaction: Dict[str, Any],
        topic: Optional[str] = None,
        key: Optional[str] = None,
        event_type: str = "c2b_confirmation",
    ) -> bool:
        """
        Publish a transaction event to Kafka.

        Args:
            transaction: Transaction data dictionary
            topic: Optional topic override
            key: Optional partition key (e.g., phone number for ordering)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Add metadata
            amount = transaction.get("TransAmount")
            event = {
                "event_type": event_type,
                "transaction_id": transaction.get("TransID"),
                "phone_number": transaction.get("MSISDN"),
                "amount": None if amount is None else str(amount),
                "account_reference": transaction.get("AccountReference")
                or transaction.get("BillRefNumber"),
                "transaction_time": transaction.get("TransTime"),
                "received_at": datetime.now().isoformat(),
                "source": "daraja_webhook",
                "data": transaction,
            }

            # Use phone number as key to ensure ordering per customer
            partition_key = key or transaction.get("MSISDN")
            return self.publish_event(event=event, topic=topic, key=partition_key)
        except Exception as e:
            logger.error("Error building transaction event: %s", str(e))
            return False

    def publish_batch(self, transactions: list, topic: Optional[str] = None) -> int:
        """
        Publish multiple transaction events.

        Args:
            transactions: List of transaction dictionaries
            topic: Optional topic override

        Returns:
            int: Number of successfully published transactions
        """
        success_count = 0

        for transaction in transactions:
            if self.publish_transaction(transaction, topic):
                success_count += 1

        # Flush to ensure all messages are sent
        self._producer.flush(10)

        logger.info(
            f"Batch published: {success_count}/{len(transactions)} transactions"
        )

        return success_count

    def publish_fraud_alert(
        self, alert: Dict[str, Any], severity: str = "medium"
    ) -> bool:
        """
        Publish a fraud alert event.

        Args:
            alert: Alert data dictionary
            severity: Alert severity level (low, medium, high, critical)

        Returns:
            bool: True if successful
        """
        fraud_event = {
            "alert_type": "fraud_detection",
            "severity": severity,
            "detected_at": datetime.now().isoformat(),
            "alert_data": alert,
        }

        return self.publish_event(
            event=fraud_event,
            topic=os.getenv("KAFKA_TOPIC_ALERTS", "mpesa-fraud-alerts"),
            key=alert.get("phone_number"),
        )

    def close(self):
        """Close the Kafka producer connection."""
        try:
            self._producer.flush(5)
            logger.info("Kafka producer closed")
        except Exception as e:
            logger.error(f"Error closing producer: {str(e)}")


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    # Initialize producer
    producer = MpesaKafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_BROKERS", "localhost:9092"),
        topic="mpesa-transactions",
    )

    # Example transaction
    sample_transaction = {
        "TransID": "TXN123456789",
        "MSISDN": "254712345678",
        "TransAmount": "5000",
        "AccountReference": "ACC001",
        "TransTime": datetime.now().isoformat(),
    }

    # Publish
    success = producer.publish_transaction(sample_transaction)
    print(f"Published: {success}")

    # Close
    producer.close()
