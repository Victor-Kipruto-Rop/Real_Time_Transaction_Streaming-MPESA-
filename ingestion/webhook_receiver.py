"""
Flask webhook receiver for M-Pesa transaction callbacks.

Receives and processes C2B validation/confirmation and B2C result callbacks
from Safaricom Daraja API.
"""

import logging
import os
from datetime import datetime
from time import time
from typing import Any, Dict, Tuple

import psycopg2
from flask import Flask, jsonify, redirect, request, send_from_directory
from pythonjsonlogger import jsonlogger

from schemas.transaction_schema import C2BConfirmationRequest, C2BValidationRequest

logger = logging.getLogger(__name__)

# Backwards-compatible placeholder for tests that patch this symbol.
db_connection = None

_RATE_STATE: Dict[Tuple[str, str], Tuple[float, int]] = {}


class WebhookProcessor:
    """Process and validate incoming webhook callbacks."""

    def __init__(self):
        """Initialize webhook processor."""

    @staticmethod
    def process_c2b_validation(payload: Dict[str, Any]) -> Dict[str, str]:
        """
        Process C2B validation callback.

        Validates incoming customer payment and returns accept/reject response.

        Args:
            payload: Webhook payload from Safaricom

        Returns:
            dict: Validation response with ResultCode and ResultDesc
        """
        try:
            C2BValidationRequest.model_validate(payload)
            # Extract transaction details
            transaction_id = payload.get("TransID")
            amount = payload.get("TransAmount")
            phone = payload.get("MSISDN")

            # Log transaction
            logger.info(
                f"C2B Validation - TxnID: {transaction_id}, " f"Amount: {amount}, Phone: {phone}"
            )

            # Validate amount (example: reject if > 1,000,000 KES)
            if amount is None:
                return {"ResultCode": "1", "ResultDesc": "Missing TransAmount"}
            if int(amount) > 1000000:
                return {"ResultCode": "1", "ResultDesc": "Amount exceeds limit"}

            # Accept transaction
            return {"ResultCode": "0", "ResultDesc": "Validation accepted"}

        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            return {"ResultCode": "1", "ResultDesc": "Validation failed"}

    def process_c2b_confirmation(self, payload: Dict[str, Any]) -> None:
        """
        Process C2B confirmation callback.

        Confirms transaction and stores in database/data warehouse.

        Args:
            payload: Webhook payload from Safaricom
        """
        try:
            C2BConfirmationRequest.model_validate(payload)
            # Extract confirmation details
            transaction_id = payload.get("TransID")
            amount = payload.get("TransAmount")
            phone = payload.get("MSISDN")
            timestamp = payload.get("TransTime")

            logger.info(
                f"C2B Confirmation - TxnID: {transaction_id}, "
                f"Amount: {amount}, Phone: {phone}, Time: {timestamp}"
            )

        except Exception as e:
            logger.error(f"Confirmation error: {str(e)}")

    def process_b2c_result(self, payload: Dict[str, Any]) -> None:
        """
        Process B2C transaction result callback.

        Handles business-to-customer payment results.

        Args:
            payload: Webhook payload from Safaricom
        """
        try:
            # Extract B2C result details
            result_code = payload.get("Result", {}).get("ResultCode")
            result_desc = payload.get("Result", {}).get("ResultDesc")
            conversation_id = payload.get("ConversationID")

            logger.info(
                f"B2C Result - Code: {result_code}, "
                f"Desc: {result_desc}, ConvID: {conversation_id}"
            )

        except Exception as e:
            logger.error(f"B2C result error: {str(e)}")

    @staticmethod
    def _validate_payload(payload: Any) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("Invalid JSON payload")
        return payload


def _configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=level)
    root = logging.getLogger()
    for handler in root.handlers:
        formatter = jsonlogger.JsonFormatter("%(levelname)s %(name)s %(message)s %(asctime)s")
        handler.setFormatter(formatter)


def create_app() -> Flask:
    """Create and configure Flask application for webhook receiver.

    Sets up routes for C2B validation/confirmation and B2C result callbacks.
    Initializes Kafka producer if brokers are configured.

    Returns:
        Flask application instance
    """
    _configure_logging()

    app = Flask(__name__)

    kafka_brokers = os.getenv("KAFKA_BROKERS", "localhost:9092").strip()
    ui_token = os.getenv("UI_TOKEN", "").strip()
    rate_limit_per_min = int(os.getenv("RATE_LIMIT_PER_MIN", "120") or "120")

    class _NoopProducer:
        def publish_transaction(self, *args, **kwargs):
            return True

        def publish_event(self, *args, **kwargs):
            return True

    def get_producer():
        if app.testing:
            # Avoid real network calls in unit tests; tests that need to assert
            # publishing behavior patch `ingestion.kafka_producer.MpesaKafkaProducer`.
            from ingestion.kafka_producer import MpesaKafkaProducer

            if getattr(MpesaKafkaProducer, "__module__", "") != "ingestion.kafka_producer":
                # Patched by tests (e.g. unittest.mock.patch), let it run.
                return MpesaKafkaProducer(
                    bootstrap_servers=kafka_brokers,
                    topic=os.getenv("KAFKA_TOPIC_TRANSACTIONS", "mpesa-transactions"),
                )
            return _NoopProducer()
        if not app.testing:
            existing = app.extensions.get("mpesa_kafka_producer")
            if existing is not None:
                return existing
        if not kafka_brokers:
            return None
        # Import inside function so unittest patching
        # `ingestion.kafka_producer.MpesaKafkaProducer` works.
        from ingestion.kafka_producer import MpesaKafkaProducer

        created = MpesaKafkaProducer(
            bootstrap_servers=kafka_brokers,
            topic=os.getenv("KAFKA_TOPIC_TRANSACTIONS", "mpesa-transactions"),
        )
        if not app.testing:
            app.extensions["mpesa_kafka_producer"] = created
        return created

    processor = WebhookProcessor()

    def _require_ui_token() -> bool:
        if not ui_token:
            return True
        provided = (
            request.headers.get("X-UI-Token", "").strip()
            or request.args.get("token", "").strip()
        )
        return provided == ui_token

    def _pg_connect():
        return psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            dbname=os.getenv("POSTGRES_DB", "mpesa_analytics"),
            user=os.getenv("POSTGRES_USER", "data_engineer"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            connect_timeout=3,
        )

    def _rate_limited(route_key: str) -> bool:
        if rate_limit_per_min <= 0:
            return False
        forwarded_for = request.headers.get("X-Forwarded-For")
        client_ip = (forwarded_for or request.remote_addr or "unknown").split(",")[0].strip()
        now = time()
        window_start, count = _RATE_STATE.get((client_ip, route_key), (now, 0))
        if now - window_start >= 60:
            _RATE_STATE[(client_ip, route_key)] = (now, 1)
            return False
        if count >= rate_limit_per_min:
            return True
        _RATE_STATE[(client_ip, route_key)] = (window_start, count + 1)
        return False

    @app.route("/", methods=["GET"])
    def root():
        return redirect("/ui", code=302)

    @app.route("/ui", methods=["GET"])
    def ui():
        if not _require_ui_token():
            return jsonify({"error": "unauthorized"}), 401
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        return send_from_directory(static_dir, "webhook_sender.html")

    @app.route("/ui/verify", methods=["GET"])
    def ui_verify():
        if not _require_ui_token():
            return jsonify({"error": "unauthorized"}), 401
        transaction_id = (request.args.get("transaction_id") or "").strip()
        if not transaction_id:
            return jsonify({"error": "missing_transaction_id"}), 400
        try:
            with _pg_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT
                          transaction_id,
                          phone_number,
                          amount,
                          transaction_time,
                          source,
                          received_at
                        FROM mpesa_transactions_raw
                        WHERE transaction_id = %s
                        """,
                        (transaction_id,),
                    )
                    row = cur.fetchone()
                    if not row:
                        return jsonify({"found": False, "transaction_id": transaction_id}), 200
                    return (
                        jsonify(
                            {
                                "found": True,
                                "transaction_id": row[0],
                                "phone_number": row[1],
                                "amount": str(row[2]),
                                "transaction_time": row[3].isoformat() if row[3] else None,
                                "source": row[4],
                                "received_at": row[5].isoformat() if row[5] else None,
                            }
                        ),
                        200,
                    )
        except Exception as e:
            logger.error("UI verify error: %s", str(e))
            return jsonify({"error": "verify_failed"}), 500

    @app.route("/webhook/c2b/validation", methods=["GET"])
    def c2b_validation_help():
        return redirect("/ui?endpoint=/webhook/c2b/validation", code=302)

    @app.route("/webhook/c2b/confirmation", methods=["GET"])
    def c2b_confirmation_help():
        return redirect("/ui?endpoint=/webhook/c2b/confirmation", code=302)

    @app.route("/webhook/b2c/result", methods=["GET"])
    def b2c_result_help():
        return redirect("/ui?endpoint=/webhook/b2c/result", code=302)

    @app.route("/webhook/c2b/validation", methods=["POST"])
    def c2b_validation():
        """Handle C2B validation callback from Safaricom.

        Validates incoming customer-to-business payment requests and returns
        accept/reject response. Publishes to Kafka if validation succeeds.
        """
        try:
            if _rate_limited("c2b_validation"):
                return jsonify({"ResultCode": "1", "ResultDesc": "Rate limit exceeded"}), 429
            payload = request.get_json(silent=True)
            if payload is None:
                return jsonify({"ResultCode": "1", "ResultDesc": "Invalid JSON"}), 400
            payload = processor._validate_payload(payload)
            logger.debug("Received C2B validation callback")
            response = processor.process_c2b_validation(payload)
            producer = get_producer()
            if response.get("ResultCode") == "0" and producer:
                # Backwards compatible call for older test suite expectations.
                producer.publish_transaction(
                    payload,
                    key=payload.get("MSISDN"),
                    event_type="c2b_validation",
                )
            return jsonify(response)
        except Exception as e:
            logger.error("Webhook validation error: %s", str(e))
            return jsonify({"ResultCode": "1", "ResultDesc": "Internal server error"}), 500

    @app.route("/webhook/c2b/confirmation", methods=["POST"])
    def c2b_confirmation():
        """Handle C2B confirmation callback from Safaricom.

        Processes completed customer-to-business transactions with full
        transaction details and account balance information.
        """
        try:
            if _rate_limited("c2b_confirmation"):
                return jsonify({"status": "error", "error": "rate_limited"}), 429
            payload = request.get_json(silent=True)
            if payload is None:
                return jsonify({"status": "error", "error": "Invalid JSON"}), 400
            payload = processor._validate_payload(payload)
            logger.debug("Received C2B confirmation callback")
            processor.process_c2b_confirmation(payload)
            producer = get_producer()
            if producer:
                producer.publish_transaction(
                    payload,
                    key=payload.get("MSISDN"),
                    event_type="c2b_confirmation",
                )
            return jsonify({"status": "received"}), 200
        except Exception as e:
            logger.error("Webhook confirmation error: %s", str(e))
            return jsonify({"status": "error"}), 500

    @app.route("/webhook/b2c/result", methods=["POST"])
    def b2c_result():
        """Handle B2C result callback from Safaricom (payout completion)."""
        try:
            if _rate_limited("b2c_result"):
                return jsonify({"status": "error", "error": "rate_limited"}), 429
            payload = request.get_json(silent=True)
            if payload is None:
                return jsonify({"status": "error", "error": "Invalid JSON"}), 400
            payload = processor._validate_payload(payload)
            logger.debug("Received B2C result callback")
            processor.process_b2c_result(payload)
            producer = get_producer()
            if producer:
                producer.publish_event(
                    event={
                        "event_type": "b2c_result",
                        "received_at": datetime.now().isoformat(),
                        "data": payload,
                    }
                )
            return jsonify({"status": "received"}), 200
        except Exception as e:
            logger.error("Webhook B2C error: %s", str(e))
            return jsonify({"status": "error"}), 500

    @app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint for webhook receiver."""
        return jsonify(
            {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "service": "mpesa-webhook-receiver",
            }
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
