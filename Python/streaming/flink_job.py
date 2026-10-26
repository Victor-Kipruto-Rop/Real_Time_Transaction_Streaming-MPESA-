"""
Apache Flink job for M-Pesa real-time transaction processing.

Performs:
- Windowed aggregations (tumbling and sliding)
- State management for running metrics
- Transaction enrichment
- Anomaly detection
- Output to Kafka and database
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Iterator, List, Tuple

logger = logging.getLogger(__name__)

# Check if PyFlink is available
try:
    from pyflink.common import Time
    from pyflink.common.serialization import (
        DeserializationSchema,
        SerializationSchema,
        Serializer,
    )
    from pyflink.common.typeinfo import Types
    from pyflink.datastream import KeyedStream, StreamExecutionEnvironment
    from pyflink.datastream.connectors.kafka import (
        FlinkKafkaConsumer,
        FlinkKafkaProducer,
    )
    from pyflink.datastream.functions import (
        FilterFunction,
        FlatMapFunction,
        KeyedProcessFunction,
        MapFunction,
        ProcessWindowFunction,
        WindowFunction,
    )
    from pyflink.datastream.state import (
        ListState,
        ListStateDescriptor,
        ValueState,
        ValueStateDescriptor,
    )
    from pyflink.datastream.window import (
        SlidingEventTimeWindows,
        TimeWindow,
        TumblingEventTimeWindows,
    )

    PYFLINK_AVAILABLE = True
except ImportError:
    PYFLINK_AVAILABLE = False
    logger.warning(
        "PyFlink not installed. Install requirements.all.txt to enable Flink streaming."
    )


if PYFLINK_AVAILABLE:

    class TransactionDeserializer(DeserializationSchema):
        """Deserialize JSON transaction messages from Kafka."""

        def deserialize(self, message: bytes) -> Dict[str, Any]:
            """Deserialize bytes to transaction dict."""
            try:
                return json.loads(message.decode("utf-8"))
            except json.JSONDecodeError as e:
                logger.error(f"Failed to deserialize message: {str(e)}")
                raise

        def is_end_of_stream(self, element: Any) -> bool:
            return False

    class TransactionSerializer(SerializationSchema):
        """Serialize transaction dict to JSON bytes for Kafka."""

        def serialize(self, element: Dict[str, Any]) -> bytes:
            """Serialize transaction dict to bytes."""
            return json.dumps(element).encode("utf-8")

    class TransactionEnricher(MapFunction):
        """Enrich transactions with additional context."""

        def map(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
            """Add enrichment fields to transaction."""
            try:
                # Extract amount category
                amount = float(transaction.get("TransAmount", 0))
                if amount < 10000:
                    transaction["amount_category"] = "low"
                elif amount < 100000:
                    transaction["amount_category"] = "medium"
                else:
                    transaction["amount_category"] = "high"

                # Standardize phone
                phone = str(transaction.get("MSISDN", "")).strip()
                if phone.startswith("+"):
                    phone = phone[1:]
                if phone.startswith("0"):
                    phone = "254" + phone[1:]
                transaction["phone_standardized"] = phone

                # Add processing timestamp
                transaction["processed_at"] = datetime.utcnow().isoformat()

                return transaction
            except Exception as e:
                logger.error(f"Error enriching transaction: {str(e)}")
                return transaction

    class VelocityDetector(KeyedProcessFunction):
        """Detect high-velocity transactions (potential fraud)."""

        VELOCITY_THRESHOLD = 5  # 5+ transactions per minute
        WINDOW_DURATION_SECS = 60

        def open(self, runtime_context):
            """Initialize state for velocity detection."""
            # State to store list of recent transaction timestamps
            state_descriptor = ListStateDescriptor("recent_transactions", Types.LONG())
            self.recent_txns_state: ListState = runtime_context.get_list_state(
                state_descriptor
            )

        def process_element(self, element: Dict[str, Any], ctx):
            """Check velocity for this transaction."""
            current_time = int(datetime.utcnow().timestamp() * 1000)

            # Get recent transaction times
            recent_times = (
                list(self.recent_txns_state.get())
                if self.recent_txns_state.get()
                else []
            )

            # Remove old transactions (outside 60-second window)
            cutoff_time = current_time - (self.WINDOW_DURATION_SECS * 1000)
            recent_times = [t for t in recent_times if t > cutoff_time]

            # Add current transaction
            recent_times.append(current_time)

            # Update state
            self.recent_txns_state.clear()
            for t in recent_times:
                self.recent_txns_state.add(t)

            # Check if velocity exceeds threshold
            if len(recent_times) > self.VELOCITY_THRESHOLD:
                element["velocity_flag"] = True
                element["recent_transaction_count"] = len(recent_times)
            else:
                element["velocity_flag"] = False

            yield element

    class HourlyAggregationFunction(WindowFunction):
        """Aggregate transactions by hour."""

        def apply(
            self, key: str, window: TimeWindow, inputs: Iterator[Dict[str, Any]], out
        ) -> None:
            """Apply hourly aggregation."""
            transactions = list(inputs)

            if not transactions:
                return

            # Aggregate metrics
            total_amount = sum(float(t.get("TransAmount", 0)) for t in transactions)
            count = len(transactions)
            avg_amount = total_amount / count if count > 0 else 0

            # Collect by amount category
            low_count = sum(
                1 for t in transactions if t.get("amount_category") == "low"
            )
            med_count = sum(
                1 for t in transactions if t.get("amount_category") == "medium"
            )
            high_count = sum(
                1 for t in transactions if t.get("amount_category") == "high"
            )

            # Create output record
            result = {
                "window_start": window.start,
                "window_end": window.end,
                "key": key,
                "transaction_count": count,
                "total_amount": total_amount,
                "avg_amount": avg_amount,
                "low_count": low_count,
                "medium_count": med_count,
                "high_count": high_count,
                "aggregation_type": "hourly",
                "timestamp": datetime.utcnow().isoformat(),
            }

            out.collect(result)

    class FifteenMinuteAggregationFunction(WindowFunction):
        """Aggregate transactions by 15 minutes."""

        def apply(
            self, key: str, window: TimeWindow, inputs: Iterator[Dict[str, Any]], out
        ) -> None:
            """Apply 15-minute aggregation."""
            transactions = list(inputs)

            if not transactions:
                return

            # Aggregate metrics
            total_amount = sum(float(t.get("TransAmount", 0)) for t in transactions)
            count = len(transactions)

            result = {
                "window_start": window.start,
                "window_end": window.end,
                "key": key,
                "transaction_count": count,
                "total_amount": total_amount,
                "aggregation_type": "15min",
                "timestamp": datetime.utcnow().isoformat(),
            }

            out.collect(result)

    class AnomalyDetector(MapFunction):
        """Detect anomalous transactions."""

        # Thresholds
        MAX_SINGLE_TRANSACTION = 500000  # 500K KES
        MIN_TRANSACTION = 1  # 1 KES

        def map(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
            """Check for anomalies."""
            amount = float(transaction.get("TransAmount", 0))

            # Check for unusually large transaction
            if amount > self.MAX_SINGLE_TRANSACTION:
                transaction["anomaly_flag"] = True
                transaction["anomaly_type"] = "unusually_large"
                transaction["risk_score"] = 85

            # Check for unusually small transaction
            elif amount < self.MIN_TRANSACTION:
                transaction["anomaly_flag"] = True
                transaction["anomaly_type"] = "invalid_amount"
                transaction["risk_score"] = 100

            # Normal transaction
            else:
                transaction["anomaly_flag"] = False
                transaction["risk_score"] = (
                    10 + (amount / self.MAX_SINGLE_TRANSACTION) * 30
                )

            return transaction

    def create_kafka_consumer(brokers: str, topics: List[str], group_id: str):
        """Create Kafka consumer for Flink."""
        return FlinkKafkaConsumer(
            topics=topics,
            deserialization_schema=TransactionDeserializer(),
            properties={
                "bootstrap.servers": brokers,
                "group.id": group_id,
                "auto.offset.reset": "earliest",
            },
        )

    def create_kafka_producer(brokers: str, topic: str):
        """Create Kafka producer for Flink."""
        return FlinkKafkaProducer(
            topic=topic,
            serialization_schema=TransactionSerializer(),
            producer_config={
                "bootstrap.servers": brokers,
                "acks": "all",
            },
        )

    def run_job():
        """Run Flink job for M-Pesa transaction processing."""

        # Configuration
        kafka_brokers = os.getenv("KAFKA_BROKERS", "localhost:9092")
        input_topic = os.getenv("KAFKA_TOPIC_TRANSACTIONS", "mpesa-transactions")
        output_topic = os.getenv("KAFKA_TOPIC_AGGREGATED", "mpesa-aggregated")
        alerts_topic = os.getenv("KAFKA_TOPIC_ALERTS", "mpesa-fraud-alerts")
        consumer_group = os.getenv("KAFKA_CONSUMER_GROUP", "mpesa-flink-group")

        # Create Flink execution environment
        env = StreamExecutionEnvironment.get_execution_environment()
        env.set_parallelism(4)

        logger.info("Starting Flink M-Pesa streaming job...")

        # Create Kafka source
        kafka_source = create_kafka_consumer(
            kafka_brokers, [input_topic], consumer_group
        )

        # Add source to stream
        transaction_stream = env.add_source(kafka_source)

        # 1. Enrich transactions
        enriched_stream = transaction_stream.map(TransactionEnricher())

        # 2. Detect anomalies
        anomaly_detected_stream = enriched_stream.map(AnomalyDetector())

        # 3. Key by phone number for stateful processing
        keyed_stream = anomaly_detected_stream.key_by(
            lambda x: x.get("MSISDN", "unknown")
        )

        # 4. Apply velocity detection
        velocity_checked_stream = keyed_stream.process(VelocityDetector())

        # 5. Create hourly aggregations (tumbling window)
        hourly_aggregations = (
            velocity_checked_stream.key_by(
                lambda x: x.get("amount_category", "unknown")
            )
            .window(TumblingEventTimeWindows.of(Time.hours(1)))
            .apply(HourlyAggregationFunction())
        )

        # 6. Create 15-minute aggregations (sliding window)
        sliding_aggregations = (
            velocity_checked_stream.key_by(
                lambda x: x.get("amount_category", "unknown")
            )
            .window(SlidingEventTimeWindows.of(Time.minutes(15), Time.minutes(5)))
            .apply(FifteenMinuteAggregationFunction())
        )

        # 7. Filter alerts (anomalies + velocity)
        alerts_stream = anomaly_detected_stream.filter(
            lambda x: x.get("anomaly_flag", False) or x.get("velocity_flag", False)
        )

        # 8. Send aggregations to Kafka
        hourly_producer = create_kafka_producer(kafka_brokers, output_topic)
        hourly_aggregations.add_sink(hourly_producer)

        sliding_producer = create_kafka_producer(kafka_brokers, output_topic)
        sliding_aggregations.add_sink(sliding_producer)

        # 9. Send alerts to separate topic
        alerts_producer = create_kafka_producer(kafka_brokers, alerts_topic)
        alerts_stream.add_sink(alerts_producer)

        # 10. Print enriched transactions to console (for debugging)
        enriched_stream.print()

        # Execute job
        logger.info("Executing Flink job...")
        env.execute("M-Pesa Real-Time Streaming Job")


def main() -> None:
    """Entry point for Flink job."""
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if not PYFLINK_AVAILABLE:
        print(
            "PyFlink is not installed. Install requirements.all.txt to enable Flink streaming."
        )
        print("\nTo run this job:")
        print("1. Install: pip install -r requirements.all.txt")
        print("2. Configure environment variables for Kafka/DB")
        print("3. Run: python -m streaming.flink_job")
        return

    logger.info("Running Flink M-Pesa streaming job...")
    kafka_brokers = os.getenv("KAFKA_BROKERS", "localhost:9092")
    input_topic = os.getenv("KAFKA_TOPIC_TRANSACTIONS", "mpesa-transactions")
    logger.info(f"Configuration: brokers={kafka_brokers}, topic={input_topic}")

    run_job()


if __name__ == "__main__":
    main()
