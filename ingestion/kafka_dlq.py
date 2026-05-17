"""
Dead Letter Queue (DLQ) Implementation for Kafka
Handles failed messages that can't be processed
Routes them to a separate topic for analysis and manual retry
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum
from kafka import KafkaProducer, KafkaConsumer
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.database.models import ErrorLog

logger = logging.getLogger(__name__)


class FailureReasonEnum(str, Enum):
    """Enum for failure reasons"""

    INVALID_SIGNATURE = "invalid_signature"
    INVALID_FORMAT = "invalid_format"
    DUPLICATE_TRANSACTION = "duplicate_transaction"
    DATABASE_ERROR = "database_error"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN_ERROR = "unknown_error"
    TIMEOUT = "timeout"
    REGION_MAPPING_FAILED = "region_mapping_failed"


@dataclass
class DeadLetterMessage:
    """Represents a message in the Dead Letter Queue"""

    message_id: str
    original_topic: str
    original_message: Dict[str, Any]
    failure_reason: FailureReasonEnum
    error_message: str
    error_stacktrace: Optional[str]
    timestamp: str
    retry_count: int = 0
    max_retries: int = 3
    is_recoverable: bool = True

    def to_json(self) -> str:
        """Convert to JSON string"""
        data = asdict(self)
        data["failure_reason"] = self.failure_reason.value
        return json.dumps(data)

    @classmethod
    def from_json(cls, json_str: str) -> "DeadLetterMessage":
        """Create from JSON string"""
        data = json.loads(json_str)
        data["failure_reason"] = FailureReasonEnum(data["failure_reason"])
        return cls(**data)


class DeadLetterQueueHandler:
    """Manages messages that fail to process"""

    def __init__(self, kafka_brokers: str = "localhost:9093"):
        """
        Initialize DLQ handler

        Args:
            kafka_brokers: Kafka broker addresses
        """
        self.kafka_brokers = kafka_brokers.split(",")
        self.dlq_topic = "mpesa-transactions-dlq"
        self.retry_topic = "mpesa-transactions-retry"
        self.dlq_producer = None
        self.dlq_consumer = None
        self.db: Optional[Session] = None

    def initialize(self):
        """Initialize Kafka producer and consumer"""
        try:
            self.dlq_producer = KafkaProducer(
                bootstrap_servers=self.kafka_brokers,
                value_serializer=lambda v: v.encode("utf-8")
                if isinstance(v, str)
                else v,
                acks="all",  # Wait for all replicas
                retries=3,
                max_in_flight_requests_per_connection=1,  # Ensure ordering
            )
            logger.info(f"DLQ Producer initialized for brokers: {self.kafka_brokers}")
        except Exception as e:
            logger.error(f"Failed to initialize DLQ producer: {e}")
            raise

    def send_to_dlq(
        self,
        message_id: str,
        original_topic: str,
        original_message: Dict[str, Any],
        failure_reason: FailureReasonEnum,
        error_message: str,
        error_stacktrace: Optional[str] = None,
        is_recoverable: bool = True,
    ) -> bool:
        """
        Send failed message to Dead Letter Queue

        Args:
            message_id: Unique ID of the message
            original_topic: Kafka topic the message came from
            original_message: The failed message content
            failure_reason: Why the message failed
            error_message: Error description
            error_stacktrace: Full error stacktrace
            is_recoverable: Whether the error might be transient

        Returns:
            True if successfully sent to DLQ
        """
        if self.dlq_producer is None:
            raise RuntimeError("DLQ producer is not initialized")

        try:
            dlq_message = DeadLetterMessage(
                message_id=message_id,
                original_topic=original_topic,
                original_message=original_message,
                failure_reason=failure_reason,
                error_message=error_message,
                error_stacktrace=error_stacktrace,
                timestamp=datetime.utcnow().isoformat(),
                is_recoverable=is_recoverable,
            )

            # Send to DLQ topic
            future = self.dlq_producer.send(
                self.dlq_topic,
                value=dlq_message.to_json(),
                key=message_id.encode() if message_id else None,
            )

            # Wait for confirmation
            record_metadata = future.get(timeout=10)

            logger.warning(
                f"Message {message_id} sent to DLQ - "
                f"Reason: {failure_reason.value} - "
                f"Topic: {record_metadata.topic}, "
                f"Partition: {record_metadata.partition}, "
                f"Offset: {record_metadata.offset}"
            )

            # Log to database
            self._log_dlq_entry(dlq_message)

            return True

        except Exception as e:
            logger.error(f"Failed to send message to DLQ: {e}", exc_info=True)
            return False

    def _log_dlq_entry(self, dlq_message: DeadLetterMessage):
        """Log DLQ entry to database"""
        try:
            db = SessionLocal()

            error_log = ErrorLog(
                transaction_id=dlq_message.message_id,
                error_type=dlq_message.failure_reason.value,
                error_message=dlq_message.error_message,
                error_stacktrace=dlq_message.error_stacktrace,
                recovery_status="pending"
                if dlq_message.is_recoverable
                else "unrecoverable",
                metadata={
                    "original_topic": dlq_message.original_topic,
                    "retry_count": dlq_message.retry_count,
                    "max_retries": dlq_message.max_retries,
                },
            )

            db.add(error_log)
            db.commit()

        except Exception as e:
            logger.error(f"Failed to log DLQ entry to database: {e}")
        finally:
            db.close()

    def send_to_retry_queue(self, dlq_message: DeadLetterMessage) -> bool:
        """
        Send message back to retry queue for reprocessing

        Args:
            dlq_message: The DLQ message to retry

        Returns:
            True if successfully sent to retry queue
        """
        if dlq_message.retry_count >= dlq_message.max_retries:
            logger.error(
                f"Message {dlq_message.message_id} exceeded max retries "
                f"({dlq_message.max_retries})"
            )
            return False

        if self.dlq_producer is None:
            raise RuntimeError("DLQ producer is not initialized")

        try:
            dlq_message.retry_count += 1
            dlq_message.timestamp = datetime.utcnow().isoformat()

            future = self.dlq_producer.send(
                self.retry_topic,
                value=dlq_message.to_json(),
                key=dlq_message.message_id.encode(),
            )

            future.get(timeout=10)

            logger.info(
                f"Message {dlq_message.message_id} sent to retry queue "
                f"(Attempt {dlq_message.retry_count}/{dlq_message.max_retries})"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to send message to retry queue: {e}")
            return False

    def start_dlq_consumer(self):
        """Start consuming messages from DLQ for monitoring/alerting"""
        try:
            self.dlq_consumer = KafkaConsumer(
                self.dlq_topic,
                bootstrap_servers=self.kafka_brokers,
                group_id="mpesa-dlq-consumer",
                value_deserializer=lambda m: m.decode("utf-8") if m else None,
                auto_offset_reset="earliest",
                enable_auto_commit=True,
            )

            logger.info(f"DLQ Consumer started for topic: {self.dlq_topic}")

            # Start consuming in background
            self._consume_dlq_messages()

        except Exception as e:
            logger.error(f"Failed to start DLQ consumer: {e}")

    def _consume_dlq_messages(self):
        """Consume and process DLQ messages"""
        if not self.dlq_consumer:
            return

        for message in self.dlq_consumer:
            try:
                dlq_message = DeadLetterMessage.from_json(message.value)

                logger.warning(
                    f"Processing DLQ message: {dlq_message.message_id} - "
                    f"Reason: {dlq_message.failure_reason.value}"
                )

                # Determine action based on failure reason
                if (
                    dlq_message.is_recoverable
                    and dlq_message.retry_count < dlq_message.max_retries
                ):
                    # Retry recoverable errors
                    self.send_to_retry_queue(dlq_message)
                else:
                    # Log for manual investigation
                    self._create_incident(dlq_message)

            except Exception as e:
                logger.error(f"Error processing DLQ message: {e}", exc_info=True)

    def _create_incident(self, dlq_message: DeadLetterMessage):
        """Create incident for manual investigation"""
        logger.error(
            f"INCIDENT: Unrecoverable DLQ message - "
            f"ID: {dlq_message.message_id}, "
            f"Reason: {dlq_message.failure_reason.value}, "
            f"Error: {dlq_message.error_message}"
        )

        # In production, this would send alerts to incident management
        # e.g., PagerDuty, Slack, email, etc.

    def get_dlq_stats(self) -> Dict[str, Any]:
        """Get DLQ statistics"""
        try:
            db = SessionLocal()

            # Count errors by type
            error_counts = (
                db.query(ErrorLog.error_type, func.count(ErrorLog.id).label("count"))
                .group_by(ErrorLog.error_type)
                .all()
            )

            # Count by recovery status
            recovery_counts = (
                db.query(
                    ErrorLog.recovery_status, func.count(ErrorLog.id).label("count")
                )
                .group_by(ErrorLog.recovery_status)
                .all()
            )

            stats = {
                "total_errors": sum(count for _, count in error_counts),
                "errors_by_type": {
                    error_type: count for error_type, count in error_counts
                },
                "errors_by_recovery_status": {
                    status: count for status, count in recovery_counts
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get DLQ stats: {e}")
            return {}
        finally:
            db.close()

    def close(self):
        """Close Kafka connections"""
        if self.dlq_producer:
            self.dlq_producer.close()
        if self.dlq_consumer:
            self.dlq_consumer.close()


# ============================================================================
# GLOBAL DLQ HANDLER INSTANCE
# ============================================================================

_dlq_handler: Optional[DeadLetterQueueHandler] = None


def get_dlq_handler() -> DeadLetterQueueHandler:
    """Get or create DLQ handler"""
    global _dlq_handler

    if _dlq_handler is None:
        _dlq_handler = DeadLetterQueueHandler()
        _dlq_handler.initialize()

    return _dlq_handler


def send_to_dlq(
    message_id: str,
    original_topic: str,
    original_message: Dict[str, Any],
    failure_reason: FailureReasonEnum,
    error_message: str,
    error_stacktrace: Optional[str] = None,
    is_recoverable: bool = True,
) -> bool:
    """Convenience function to send message to DLQ"""
    handler = get_dlq_handler()
    return handler.send_to_dlq(
        message_id=message_id,
        original_topic=original_topic,
        original_message=original_message,
        failure_reason=failure_reason,
        error_message=error_message,
        error_stacktrace=error_stacktrace,
        is_recoverable=is_recoverable,
    )


if __name__ == "__main__":
    """Test DLQ functionality"""
    import logging

    logging.basicConfig(level=logging.INFO)

    handler = DeadLetterQueueHandler()
    handler.initialize()

    # Example: Send a test message to DLQ
    test_message = {
        "TransactionType": "Pay Bills Online",
        "TransID": "TXN123",
        "TransAmount": "1000",
        "MSISDN": "254712345678",
    }

    success = handler.send_to_dlq(
        message_id="test-123",
        original_topic="mpesa-transactions",
        original_message=test_message,
        failure_reason=FailureReasonEnum.INVALID_SIGNATURE,
        error_message="HMAC signature verification failed",
    )

    print(f"Sent to DLQ: {success}")

    # Get statistics
    stats = handler.get_dlq_stats()
    print(f"DLQ Stats: {json.dumps(stats, indent=2)}")

    handler.close()
