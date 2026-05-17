"""
Metrics collection for M-Pesa streaming pipeline.

Collects and exposes Prometheus metrics for Grafana dashboards
and monitoring systems.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import prometheus_client, provide no-op fallbacks if not available
try:
    from prometheus_client import Counter, Gauge, Histogram, Summary

    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False

    # Define no-op metric classes for when prometheus_client is not installed
    class _NoOpMetric:
        def inc(self, amount: float = 1):
            pass

        def dec(self, amount: float = 1):
            pass

        def set(self, value: float):
            pass

        def observe(self, value: float):
            pass

        def labels(self, **kwargs):
            return self

        def time(self):
            class NoOpTimer:
                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    pass

            return NoOpTimer()

    Counter = _NoOpMetric  # type: ignore[misc,assignment]
    Gauge = _NoOpMetric  # type: ignore[misc,assignment]
    Histogram = _NoOpMetric  # type: ignore[misc,assignment]
    Summary = _NoOpMetric  # type: ignore[misc,assignment]


class MetricsCollector:
    """Collect and expose pipeline metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.enabled = HAS_PROMETHEUS
        self._initialize_metrics()

    def _initialize_metrics(self) -> None:
        """Initialize all Prometheus metrics."""
        # Message processing metrics
        self.messages_processed = Counter(
            "mpesa_messages_processed_total",
            "Total M-Pesa messages processed",
            ["source"],
        )

        self.messages_failed = Counter(
            "mpesa_messages_failed_total",
            "Total M-Pesa messages that failed processing",
            ["error_type"],
        )

        self.message_processing_time = Histogram(
            "mpesa_message_processing_seconds",
            "Time taken to process M-Pesa messages",
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
        )

        # Kafka metrics
        self.kafka_consumer_lag = Gauge(
            "mpesa_kafka_consumer_lag",
            "Current Kafka consumer lag in messages",
            ["topic", "partition"],
        )

        self.kafka_messages_consumed = Counter(
            "mpesa_kafka_messages_consumed_total",
            "Total Kafka messages consumed",
            ["topic"],
        )

        self.kafka_connection_errors = Counter(
            "mpesa_kafka_connection_errors_total",
            "Total Kafka connection errors",
        )

        # Database metrics
        self.database_operations = Counter(
            "mpesa_database_operations_total",
            "Total database operations",
            ["operation", "status"],
        )

        self.database_operation_time = Histogram(
            "mpesa_database_operation_seconds",
            "Time taken for database operations",
            ["operation"],
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0),
        )

        self.database_connection_pool_size = Gauge(
            "mpesa_database_connection_pool_size",
            "Current database connection pool size",
        )

        self.database_connection_errors = Counter(
            "mpesa_database_connection_errors_total",
            "Total database connection errors",
        )

        # Transaction metrics
        self.transactions_processed = Counter(
            "mpesa_transactions_processed_total",
            "Total transactions processed",
            ["status"],
        )

        self.transaction_amount_sum = Gauge(
            "mpesa_transaction_amount_sum_ksh",
            "Total transaction amount in KSH",
            ["time_window"],
        )

        self.transaction_amount_histogram = Histogram(
            "mpesa_transaction_amount_ksh",
            "Distribution of transaction amounts",
            buckets=(100, 500, 1000, 5000, 10000, 50000, 100000, 500000),
        )

        self.unique_customers_gauge = Gauge(
            "mpesa_unique_customers_count",
            "Number of unique customers",
            ["time_window"],
        )

        # Validation metrics
        self.validation_failures = Counter(
            "mpesa_validation_failures_total",
            "Total validation failures",
            ["validation_type"],
        )

        # API metrics
        self.webhook_requests = Counter(
            "mpesa_webhook_requests_total",
            "Total webhook requests received",
            ["endpoint", "status_code"],
        )

        self.webhook_latency = Histogram(
            "mpesa_webhook_latency_seconds",
            "Webhook request latency",
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0),
        )

        self.daraja_api_calls = Counter(
            "mpesa_daraja_api_calls_total",
            "Total Daraja API calls",
            ["endpoint", "status"],
        )

        self.daraja_api_latency = Histogram(
            "mpesa_daraja_api_latency_seconds",
            "Daraja API response time",
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0),
        )

        # dbt metrics
        self.dbt_test_executions = Counter(
            "mpesa_dbt_test_executions_total",
            "Total dbt test executions",
            ["status"],
        )

        self.dbt_model_rows = Gauge(
            "mpesa_dbt_model_rows",
            "Number of rows in dbt model",
            ["model_name"],
        )

        # System metrics
        self.pipeline_errors = Counter(
            "mpesa_pipeline_errors_total",
            "Total pipeline errors",
            ["component"],
        )

        self.pipeline_health = Gauge(
            "mpesa_pipeline_health",
            "Pipeline health status (1=healthy, 0=unhealthy)",
        )

        self.data_freshness_age_seconds = Gauge(
            "mpesa_data_freshness_age_seconds",
            "Age of most recent data in seconds",
        )

        logger.info("Metrics collector initialized")

    def record_message_processed(self, source: str = "webhook") -> None:
        """Record a processed message."""
        self.messages_processed.labels(source=source).inc()

    def record_message_failed(self, error_type: str) -> None:
        """Record a failed message."""
        self.messages_failed.labels(error_type=error_type).inc()

    def record_transaction_processed(self, status: str = "success") -> None:
        """Record a processed transaction."""
        self.transactions_processed.labels(status=status).inc()

    def record_transaction_amount(self, amount: float) -> None:
        """Record transaction amount."""
        self.transaction_amount_histogram.observe(amount)

    def record_kafka_consumer_lag(self, topic: str, partition: int, lag: int) -> None:
        """Record Kafka consumer lag."""
        self.kafka_consumer_lag.labels(topic=topic, partition=partition).set(lag)

    def record_database_operation(
        self, operation: str, duration: float, status: str = "success"
    ) -> None:
        """Record database operation."""
        self.database_operations.labels(operation=operation, status=status).inc()
        self.database_operation_time.labels(operation=operation).observe(duration)

    def record_webhook_request(
        self, endpoint: str, status_code: int, duration: float
    ) -> None:
        """Record webhook request."""
        self.webhook_requests.labels(endpoint=endpoint, status_code=status_code).inc()
        self.webhook_latency.observe(duration)

    def record_daraja_api_call(
        self, endpoint: str, status: str, duration: float
    ) -> None:
        """Record Daraja API call."""
        self.daraja_api_calls.labels(endpoint=endpoint, status=status).inc()
        self.daraja_api_latency.observe(duration)

    def record_validation_failure(self, validation_type: str) -> None:
        """Record validation failure."""
        self.validation_failures.labels(validation_type=validation_type).inc()

    def record_dbt_test_execution(self, status: str = "passed") -> None:
        """Record dbt test execution."""
        self.dbt_test_executions.labels(status=status).inc()

    def set_dbt_model_rows(self, model_name: str, row_count: int) -> None:
        """Set row count for dbt model."""
        self.dbt_model_rows.labels(model_name=model_name).set(row_count)

    def record_pipeline_error(self, component: str) -> None:
        """Record pipeline error."""
        self.pipeline_errors.labels(component=component).inc()

    def set_pipeline_health(self, healthy: bool) -> None:
        """Set pipeline health status."""
        self.pipeline_health.set(1 if healthy else 0)

    def set_data_freshness_age(self, age_seconds: float) -> None:
        """Set data freshness age."""
        self.data_freshness_age_seconds.set(age_seconds)

    def set_unique_customers_count(
        self, count: int, time_window: str = "hourly"
    ) -> None:
        """Set unique customers count."""
        self.unique_customers_gauge.labels(time_window=time_window).set(count)

    def set_transaction_amount_sum(
        self, amount_sum: float, time_window: str = "hourly"
    ) -> None:
        """Set transaction amount sum."""
        self.transaction_amount_sum.labels(time_window=time_window).set(amount_sum)

    def get_metrics_endpoint(self):
        """Get Prometheus metrics for scraping."""
        if HAS_PROMETHEUS:
            from prometheus_client import REGISTRY, generate_latest

            return generate_latest(REGISTRY)
        else:
            return b"Prometheus client not installed"


_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get singleton metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collector = get_metrics_collector()

    # Record some sample metrics
    print("Recording sample metrics...")
    collector.record_message_processed("webhook")
    collector.record_transaction_processed("success")
    collector.record_transaction_amount(5000.0)
    collector.record_database_operation("insert", 0.05, "success")
    collector.set_pipeline_health(True)
    collector.set_data_freshness_age(15.0)

    print("Metrics recorded successfully")
