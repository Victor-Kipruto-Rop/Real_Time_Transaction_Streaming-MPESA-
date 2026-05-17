"""
Flask webhook receiver for M-Pesa transaction callbacks.

Receives and processes C2B validation/confirmation, B2C result callbacks,
and STK Push callbacks from Safaricom Daraja API.
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

db_connection = None

_RATE_STATE: Dict[Tuple[str, str], Tuple[float, int]] = {}


class WebhookProcessor:
    """Process and validate incoming webhook callbacks."""

    @staticmethod
    def process_c2b_validation(payload: Dict[str, Any]) -> Dict[str, str]:
        try:
            C2BValidationRequest.model_validate(payload)

            transaction_id = payload.get("TransID")
            amount = payload.get("TransAmount")
            phone = payload.get("MSISDN")

            logger.info(
                "C2B Validation - TxnID: %s, Amount: %s, Phone: %s",
                transaction_id,
                amount,
                phone,
            )

            if amount is None:
                return {"ResultCode": "1", "ResultDesc": "Missing TransAmount"}

            if int(amount) > 1000000:
                return {"ResultCode": "1", "ResultDesc": "Amount exceeds limit"}

            return {"ResultCode": "0", "ResultDesc": "Validation accepted"}

        except Exception as e:
            logger.error("Validation error: %s", str(e))
            return {"ResultCode": "1", "ResultDesc": "Validation failed"}

    def process_c2b_confirmation(self, payload: Dict[str, Any]) -> None:
        try:
            C2BConfirmationRequest.model_validate(payload)

            transaction_id = payload.get("TransID")
            amount = payload.get("TransAmount")
            phone = payload.get("MSISDN")
            timestamp = payload.get("TransTime")

            logger.info(
                "C2B Confirmation - TxnID: %s, Amount: %s, Phone: %s, Time: %s",
                transaction_id,
                amount,
                phone,
                timestamp,
            )

        except Exception as e:
            logger.error("Confirmation error: %s", str(e))

    def process_b2c_result(self, payload: Dict[str, Any]) -> None:
        try:
            result_code = payload.get("Result", {}).get("ResultCode")
            result_desc = payload.get("Result", {}).get("ResultDesc")
            conversation_id = payload.get("ConversationID")

            logger.info(
                "B2C Result - Code: %s, Desc: %s, ConvID: %s",
                result_code,
                result_desc,
                conversation_id,
            )

        except Exception as e:
            logger.error("B2C result error: %s", str(e))

    def process_stk_callback(self, payload: Dict[str, Any]) -> None:
        try:
            body = payload.get("Body", {})
            stk_callback = body.get("stkCallback", {})

            merchant_request_id = stk_callback.get("MerchantRequestID")
            checkout_request_id = stk_callback.get("CheckoutRequestID")
            result_code = stk_callback.get("ResultCode")
            result_desc = stk_callback.get("ResultDesc")

            logger.info(
                "STK Callback - MerchantRequestID: %s, CheckoutRequestID: %s, "
                "ResultCode: %s, ResultDesc: %s",
                merchant_request_id,
                checkout_request_id,
                result_code,
                result_desc,
            )

        except Exception as e:
            logger.error("STK callback processing error: %s", str(e))

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
        formatter = jsonlogger.JsonFormatter(
            "%(levelname)s %(name)s %(message)s %(asctime)s"
        )
        handler.setFormatter(formatter)


def create_app() -> Flask:
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
            from ingestion.kafka_producer import MpesaKafkaProducer

            if (
                getattr(MpesaKafkaProducer, "__module__", "")
                != "ingestion.kafka_producer"
            ):
                return MpesaKafkaProducer(
                    bootstrap_servers=kafka_brokers,
                    topic=os.getenv("KAFKA_TOPIC_TRANSACTIONS", "mpesa-transactions"),
                )

            return _NoopProducer()

        existing = app.extensions.get("mpesa_kafka_producer")

        if existing is not None:
            return existing

        if not kafka_brokers:
            return None

        from ingestion.kafka_producer import MpesaKafkaProducer

        created = MpesaKafkaProducer(
            bootstrap_servers=kafka_brokers,
            topic=os.getenv("KAFKA_TOPIC_TRANSACTIONS", "mpesa-transactions"),
        )

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
        client_ip = (
            (forwarded_for or request.remote_addr or "unknown").split(",")[0].strip()
        )

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
        return (
            jsonify(
                {
                    "service": "mpesa-webhook-receiver",
                    "status": "running",
                    "timestamp": datetime.now().isoformat(),
                    "endpoints": {
                        "ui": "/ui",
                        "health": "/health",
                        "c2b_validation": "/webhook/c2b/validation",
                        "c2b_confirmation": "/webhook/c2b/confirmation",
                        "b2c_result": "/webhook/b2c/result",
                        "stk_callback": "/webhook/stk/callback",
                    },
                }
            ),
            200,
        )

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
                        return (
                            jsonify(
                                {
                                    "found": False,
                                    "transaction_id": transaction_id,
                                }
                            ),
                            200,
                        )

                    return (
                        jsonify(
                            {
                                "found": True,
                                "transaction_id": row[0],
                                "phone_number": row[1],
                                "amount": str(row[2]),
                                "transaction_time": row[3].isoformat()
                                if row[3]
                                else None,
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

    @app.route("/webhook/stk/callback", methods=["GET"])
    def stk_callback_help():
        return redirect("/ui?endpoint=/webhook/stk/callback", code=302)

    @app.route("/webhook/c2b/validation", methods=["POST"])
    def c2b_validation():
        try:
            if _rate_limited("c2b_validation"):
                return (
                    jsonify(
                        {
                            "ResultCode": "1",
                            "ResultDesc": "Rate limit exceeded",
                        }
                    ),
                    429,
                )

            payload = request.get_json(silent=True)

            if payload is None:
                return (
                    jsonify(
                        {
                            "ResultCode": "1",
                            "ResultDesc": "Invalid JSON",
                        }
                    ),
                    400,
                )

            payload = processor._validate_payload(payload)

            logger.debug("Received C2B validation callback")

            response = processor.process_c2b_validation(payload)

            producer = get_producer()

            if response.get("ResultCode") == "0" and producer:
                producer.publish_transaction(
                    payload,
                    key=payload.get("MSISDN"),
                    event_type="c2b_validation",
                )

            return jsonify(response)

        except Exception as e:
            logger.error("Webhook validation error: %s", str(e))
            return (
                jsonify(
                    {
                        "ResultCode": "1",
                        "ResultDesc": "Internal server error",
                    }
                ),
                500,
            )

    @app.route("/webhook/c2b/confirmation", methods=["POST"])
    def c2b_confirmation():
        try:
            if _rate_limited("c2b_confirmation"):
                return (
                    jsonify(
                        {
                            "status": "error",
                            "error": "rate_limited",
                        }
                    ),
                    429,
                )

            payload = request.get_json(silent=True)

            if payload is None:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "error": "Invalid JSON",
                        }
                    ),
                    400,
                )

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
        try:
            if _rate_limited("b2c_result"):
                return (
                    jsonify(
                        {
                            "status": "error",
                            "error": "rate_limited",
                        }
                    ),
                    429,
                )

            payload = request.get_json(silent=True)

            if payload is None:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "error": "Invalid JSON",
                        }
                    ),
                    400,
                )

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

    @app.route("/webhook/stk/callback", methods=["POST"])
    def stk_callback():
        try:
            if _rate_limited("stk_callback"):
                return (
                    jsonify(
                        {
                            "status": "error",
                            "error": "rate_limited",
                        }
                    ),
                    429,
                )

            payload = request.get_json(silent=True)

            if payload is None:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "error": "Invalid JSON",
                        }
                    ),
                    400,
                )

            payload = processor._validate_payload(payload)

            logger.debug("Received STK Push callback")

            processor.process_stk_callback(payload)

            producer = get_producer()

            if producer:
                producer.publish_event(
                    event={
                        "event_type": "stk_callback",
                        "received_at": datetime.now().isoformat(),
                        "data": payload,
                    }
                )

            return (
                jsonify(
                    {
                        "ResultCode": 0,
                        "ResultDesc": "STK callback received",
                    }
                ),
                200,
            )

        except Exception as e:
            logger.error("STK callback error: %s", str(e))
            return jsonify({"status": "error"}), 500

    @app.route("/health", methods=["GET"])
    def health_check():
        return (
            jsonify(
                {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "service": "mpesa-webhook-receiver",
                }
            ),
            200,
        )

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
