"""
Alerting system for M-Pesa streaming pipeline.

Sends alerts to Slack, email, and external monitoring services
when pipeline issues are detected.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AlertManager:
    """Manage pipeline alerts and notifications."""

    def __init__(self):
        """Initialize alert manager."""
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        self.email_recipients = os.getenv("ALERT_EMAIL_RECIPIENTS", "").split(",")
        self.sentry_dsn = os.getenv("SENTRY_DSN")
        self.pagerduty_key = os.getenv("PAGERDUTY_INTEGRATION_KEY")

    def send_slack_alert(
        self,
        message: str,
        severity: str = "warning",
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send alert to Slack."""
        if not self.slack_webhook:
            logger.warning("Slack webhook not configured")
            return False

        try:
            import requests

            color_map = {
                "error": "#FF0000",
                "warning": "#FFA500",
                "info": "#0099FF",
                "success": "#00FF00",
            }

            fields = [
                {
                    "title": "Timestamp",
                    "value": datetime.utcnow().isoformat(),
                },
                {
                    "title": "Environment",
                    "value": os.getenv("ENVIRONMENT", "unknown"),
                },
            ]

            if details:
                fields.extend({"title": k, "value": str(v)} for k, v in details.items())

            payload = {
                "attachments": [
                    {
                        "color": color_map.get(severity, "#808080"),
                        "title": f"M-Pesa Pipeline Alert - {severity.upper()}",
                        "text": message,
                        "fields": fields,
                        "footer": "M-Pesa Streaming Pipeline",
                    }
                ]
            }

            response = requests.post(self.slack_webhook, json=payload, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False

    def send_email_alert(
        self,
        subject: str,
        body: str,
        severity: str = "warning",
    ) -> bool:
        """Send alert via email."""
        if not self.email_recipients or not self.email_recipients[0]:
            logger.warning("Email recipients not configured")
            return False

        try:
            import smtplib
            from email.mime.text import MIMEText

            smtp_server = os.getenv("SMTP_SERVER", "localhost")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            sender = os.getenv("ALERT_EMAIL_SENDER", "alerts@mpesa-pipeline.local")

            message = MIMEText(body)
            message["Subject"] = f"[{severity.upper()}] {subject}"
            message["From"] = sender
            message["To"] = ", ".join(self.email_recipients)

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if os.getenv("SMTP_TLS"):
                    server.starttls()
                smtp_user = os.getenv("SMTP_USER")
                smtp_password = os.getenv("SMTP_PASSWORD")
                if smtp_user and smtp_password:
                    server.login(smtp_user, smtp_password)
                server.send_message(message)

            logger.info(f"Email alert sent to {', '.join(self.email_recipients)}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False

    def alert_kafka_connectivity_failure(self, error: str) -> None:
        """Alert when Kafka connection fails."""
        message = f"Kafka connectivity check failed. Error: {error}"
        self.send_slack_alert(
            message,
            severity="error",
            details={"component": "Kafka", "error": error},
        )
        self.send_email_alert(
            "Kafka Connectivity Failure",
            f"The M-Pesa pipeline cannot connect to Kafka.\n\nError: {error}",
            severity="error",
        )

    def alert_database_connectivity_failure(self, error: str) -> None:
        """Alert when database connection fails."""
        message = f"Database connectivity check failed. Error: {error}"
        self.send_slack_alert(
            message,
            severity="error",
            details={"component": "PostgreSQL", "error": error},
        )
        self.send_email_alert(
            "Database Connectivity Failure",
            f"The M-Pesa pipeline cannot connect to PostgreSQL.\n\nError: {error}",
            severity="error",
        )

    def alert_high_consumer_lag(self, lag: int, threshold: int = 10000) -> None:
        """Alert when consumer lag exceeds threshold."""
        message = f"Consumer lag is high: {lag} messages (threshold: {threshold})"
        self.send_slack_alert(
            message,
            severity="warning",
            details={"component": "Kafka Consumer", "lag": lag, "threshold": threshold},
        )

    def alert_data_staleness(
        self, staleness_seconds: int, threshold: int = 300
    ) -> None:
        """Alert when data becomes stale."""
        message = (
            f"Data staleness warning: {staleness_seconds}s (threshold: {threshold}s)"
        )
        self.send_slack_alert(
            message,
            severity="warning",
            details={
                "component": "Data Pipeline",
                "staleness_seconds": staleness_seconds,
                "threshold_seconds": threshold,
            },
        )

    def alert_transaction_volume_anomaly(
        self,
        expected_volume: int,
        actual_volume: int,
        threshold_percent: float = 20.0,
    ) -> None:
        """Alert when transaction volume deviates significantly."""
        deviation = abs(actual_volume - expected_volume)
        deviation_percent = (
            (deviation / expected_volume * 100) if expected_volume > 0 else 0
        )

        message = (
            f"Transaction volume anomaly detected. Expected: {expected_volume}, "
            f"Actual: {actual_volume} ({deviation_percent:.1f}% deviation)"
        )

        self.send_slack_alert(
            message,
            severity="warning",
            details={
                "component": "Transaction Volume",
                "expected": expected_volume,
                "actual": actual_volume,
                "deviation_percent": f"{deviation_percent:.1f}%",
            },
        )

    def alert_webhook_failure(self, status_code: int, error: str) -> None:
        """Alert when webhook receiver fails."""
        message = f"Webhook receiver error (HTTP {status_code}): {error}"
        self.send_slack_alert(
            message,
            severity="error",
            details={"component": "Webhook Receiver", "status_code": status_code},
        )

    def alert_dbt_test_failure(self, test_name: str, error: str) -> None:
        """Alert when dbt tests fail."""
        message = f"dbt test failed: {test_name}. {error}"
        self.send_slack_alert(
            message,
            severity="error",
            details={"component": "dbt", "test": test_name},
        )
        self.send_email_alert(
            "dbt Test Failure",
            f"The data quality test '{test_name}' failed.\n\nError: {error}",
            severity="error",
        )

    def alert_fraud_detected(
        self, transaction_id: str, details: Dict[str, Any]
    ) -> None:
        """Alert when fraud is detected."""
        message = f"Potential fraud detected in transaction {transaction_id}"
        self.send_slack_alert(
            message,
            severity="warning",
            details={"transaction_id": transaction_id, **details},
        )

    def alert_processing_latency_high(
        self, latency_ms: float, threshold_ms: float = 1000.0
    ) -> None:
        """Alert when processing latency is high."""
        message = f"Processing latency is high: {latency_ms:.1f}ms (threshold: {threshold_ms}ms)"
        self.send_slack_alert(
            message,
            severity="warning",
            details={
                "component": "Stream Processing",
                "latency_ms": f"{latency_ms:.1f}",
                "threshold_ms": f"{threshold_ms:.1f}",
            },
        )

    def alert_pipeline_recovery(self, component: str, details: str) -> None:
        """Alert when pipeline recovers from an issue."""
        message = f"{component} has recovered and is operational"
        self.send_slack_alert(
            message,
            severity="success",
            details={"component": component, "details": details},
        )


def get_alert_manager() -> AlertManager:
    """Get singleton alert manager instance."""
    return AlertManager()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    manager = AlertManager()

    # Test alerts
    print("Testing Slack alert...")
    manager.send_slack_alert(
        "This is a test alert",
        severity="info",
        details={"test": "yes"},
    )

    print("Testing email alert...")
    manager.send_email_alert(
        "Test Subject",
        "This is a test email alert",
        severity="info",
    )
