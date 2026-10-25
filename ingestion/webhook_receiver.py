"""
Flask webhook receiver for M-Pesa transaction callbacks.

Receives and processes C2B validation/confirmation, B2C result callbacks,
and STK Push callbacks from Safaricom Daraja API.
"""

import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, Tuple

import psycopg2
from flask import Flask, jsonify, redirect, request, send_from_directory
from pythonjsonlogger import jsonlogger

from app.config import settings
from app.database.outbox import enqueue_callback
from ingestion.metrics import get_metrics_collector
from schemas.transaction_schema import C2BConfirmationRequest, C2BValidationRequest


logger = logging.getLogger(__name__)

db_connection = None

_RATE_STATE: Dict[Tuple[str, str], Tuple[float, int]] = {}


def _verify_webhook_signature(payload: Dict[str, Any], signature: str | None) -> None:
    secret = (settings.WEBHOOK_SIGNING_SECRET or "").strip()
    if not secret and settings.REQUIRE_WEBHOOK_SIGNATURE:
        raise ValueError("WEBHOOK_SIGNING_SECRET is not configured")
    if not secret:
        return
    if not signature:
        raise ValueError("missing webhook signature")
    expected = hmac.new(secret.encode("utf-8"), _canonical_payload(payload).encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("invalid webhook signature")


def _check_replay(payload: Dict[str, Any], event_type: str) -> None:
    _prune_replay_cache()
    key = _get_replay_key(payload, event_type)
    redis_client = _get_redis_replay_client()
    replay_key = f"webhook:replay:{key}"

    if redis_client:
        if redis_client.exists(replay_key):
            raise ValueError("duplicate or replayed webhook payload")
    elif key in _REPLAY_CACHE:
        raise ValueError("duplicate or replayed webhook payload")

    # Callback-event identity is scoped by event_type. Do not populate the
    # transaction_id uniqueness field here: validation and confirmation can
    # legitimately reference the same transaction identifier.
    if mark_event_seen(
        event_key=key,
        transaction_id=None,
        payload=payload,
        source=f"webhook:{event_type}",
    ):
        raise ValueError("duplicate or replayed webhook payload")

    if redis_client:
        if not redis_client.set(replay_key, "1", ex=settings.REPLAY_TTL_SECONDS, nx=True):
            raise ValueError("duplicate or replayed webhook payload")
    else:
        _REPLAY_CACHE[key] = time.monotonic()


def _replay_backend_status() -> str:
    if _get_redis_replay_client() is not None:
        return "redis"
    return "memory"


def _verify_request_signature(payload: Dict[str, Any]) -> None:
    signature = (
        request.headers.get("X-Safaricom-Signature")
        or request.headers.get("X-Signature")
        or request.headers.get("X-Mpesa-Signature")
    )
    _verify_webhook_signature(payload, signature)


def validate_b2c_payload(payload: Dict[str, Any]) -> bool:
    """Validate the documented outer shape of a Daraja B2C result callback."""
    result = payload.get("Result")
    if not isinstance(result, dict):
        return False
    if not isinstance(result.get("ResultCode"), (int, str)) or isinstance(result.get("ResultCode"), bool):
        return False
    if not str(result.get("ResultCode", "")).strip().lstrip("-").isdigit():
        return False
    if not isinstance(result.get("ResultDesc"), str) or not result.get("ResultDesc").strip():
        return False
    if not (payload.get("ConversationID") or result.get("ConversationID") or result.get("OriginatorConversationID")):
        return False
    return True


def validate_stk_payload(payload: Dict[str, Any]) -> bool:
    """Validate the documented outer shape of a Daraja STK callback."""
    body = payload.get("Body")
    if not isinstance(body, dict):
        return False
    callback = body.get("stkCallback")
    if not isinstance(callback, dict):
        return False
    if not isinstance(callback.get("MerchantRequestID"), str) or not callback["MerchantRequestID"].strip():
        return False
    if not isinstance(callback.get("CheckoutRequestID"), str) or not callback["CheckoutRequestID"].strip():
        return False
    result_code = callback.get("ResultCode")
    if not isinstance(result_code, (int, str)) or isinstance(result_code, bool):
        return False
    if not str(result_code).strip().lstrip("-").isdigit():
        return False
    if not isinstance(callback.get("ResultDesc"), str) or not callback["ResultDesc"].strip():
        return False
    metadata = callback.get("CallbackMetadata")
    if metadata is not None:
        if not isinstance(metadata, dict) or not isinstance(metadata.get("Item", []), list):
            return False
    return True


def validate_c2b_payload(payload: Dict[str, Any]) -> bool:
    """Strictly validate C2B payloads for required fields, types, and safe ranges."""
    try:
        C2BConfirmationRequest.model_validate(payload)
        return True
    except Exception:
        return False


def _blocked_webhook_context(payload: Dict[str, Any], reason: str) -> None:
    # Do not trust X-Forwarded-For unless a correctly configured trusted-proxy
    # middleware is deployed. Direct clients can spoof this header.
    client_ip = request.remote_addr or "unknown"
    transaction_id = str(payload.get("TransID") or payload.get("transaction_id") or "")
    signature_present = bool(
        request.headers.get("X-Safaricom-Signature")
        or request.headers.get("X-Signature")
        or request.headers.get("X-Mpesa-Signature")
    )
    logger.warning(
        "Blocked webhook: source_ip=%s transaction_id=%s reason=%s signature_present=%s endpoint=%s",
        client_ip,
        transaction_id,
        reason,
        signature_present,
        request.path,
    )
    get_metrics_collector().record_webhook_security_event(reason)


class WebhookProcessor:
    """Process and validate incoming webhook callbacks."""

    @staticmethod
    def process_c2b_validation(payload: Dict[str, Any]) -> Dict[str, str]:
        try:
            transaction_id = payload.get("TransID")
            amount = payload.get("TransAmount")
            phone = payload.get("MSISDN")
            trans_time = payload.get("TransTime")

            if not (transaction_id and amount and phone and trans_time):
                return {"ResultCode": 1, "ResultDesc": "Missing required fields"}

            datetime.strptime(str(trans_time), "%Y%m%d%H%M%S")

            logger.info(
                "C2B Validation - TxnID: %s, Amount: %s, Phone: %s",
                transaction_id,
                amount,
                phone,
            )

            if amount is None:
                return {"ResultCode": 1, "ResultDesc": "Missing TransAmount"}

            if float(amount) > 1000000:
                return {"ResultCode": 1, "ResultDesc": "Amount exceeds limit"}

            return {"ResultCode": 0, "ResultDesc": "Validation accepted"}

        except Exception as e:
            logger.error("Validation error: %s", str(e))
            return {"ResultCode": 1, "ResultDesc": "Validation failed"}

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
    # Reject oversized callback bodies before parsing JSON. Keep this configurable
    # for provider payload changes, but bounded by default.
    app.config["MAX_CONTENT_LENGTH"] = max(
        1024, int(os.getenv("MAX_WEBHOOK_BODY_BYTES", "65536"))
    )

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
    from ingestion.metrics import WebhookMetrics

    def _require_ui_token() -> bool:
        # A missing server-side token must disable the UI, not make it public.
        # Header auth is preferred. Query-string support remains for the browser demo
        # page, which forwards its token in X-UI-Token on API requests; use only in
        # local/sandbox environments because URLs can be retained in browser/proxy logs.
        if not ui_token:
            return False
        provided = (
            request.headers.get("X-UI-Token", "").strip()
            or request.args.get("token", "").strip()
        )
        return hmac.compare_digest(provided, ui_token)

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

        # Use the direct peer address. If this app is behind a proxy, configure
        # trusted proxy handling at the deployment boundary instead of trusting
        # arbitrary client-supplied X-Forwarded-For values.
        client_ip = request.remote_addr or "unknown"

        now = time.time()
        window_start, count = _RATE_STATE.get((client_ip, route_key), (now, 0))

        if now - window_start >= 60:
            _RATE_STATE[(client_ip, route_key)] = (now, 1)
            return False

        if count >= rate_limit_per_min:
            return True

        _RATE_STATE[(client_ip, route_key)] = (window_start, count + 1)
        return False

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify({"ResultCode": "1", "ResultDesc": "Payload too large"}), 413

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
                                "transaction_time": (
                                    row[3].isoformat()
                                    if hasattr(row[3], "isoformat")
                                    else str(row[3]) if row[3] is not None else None
                                ),
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

            if not validate_c2b_payload(payload):
                get_metrics_collector().record_validation_failure("c2b_payload")
                return jsonify({"ResultCode": 1, "ResultDesc": "Invalid payload"}), 400

            try:
                _verify_request_signature(payload)
            except ValueError as exc:
                reason = str(exc)
                _blocked_webhook_context(payload, reason)
                return jsonify({"ResultCode": "1", "ResultDesc": reason}), 401

            logger.debug("Received C2B validation callback")

            response = processor.process_c2b_validation(payload)

            if str(response.get("ResultCode")) == "0":
                event_key, created = enqueue_callback("c2b_validation", payload)
                logger.info("C2B validation callback durably accepted", extra={"event_key": event_key, "outbox_created": created})

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
        started = time.time()
        try:
            if _rate_limited("c2b_confirmation"):
                status = 429
                response = jsonify({"status": "error", "error": "rate_limited"}), status
                WebhookMetrics.record_request(status, time.time() - started)
                return response

            payload = request.get_json(silent=True)

            if payload is None:
                status = 400
                response = jsonify({"status": "error", "error": "Invalid JSON"}), status
                WebhookMetrics.record_request(status, time.time() - started)
                return response

            payload = processor._validate_payload(payload)

            if not validate_c2b_payload(payload):
                get_metrics_collector().record_validation_failure("c2b_payload")
                status = 400
                response = jsonify({"ResultCode": 1, "ResultDesc": "Invalid payload"}), status
                WebhookMetrics.record_request(status, time.time() - started)
                return response

            try:
                _verify_request_signature(payload)
            except ValueError as exc:
                reason = str(exc)
                _blocked_webhook_context(payload, reason)
                response = jsonify({"status": "error", "error": reason}), 401
                WebhookMetrics.record_request(401, time.time() - started)
                return response

            logger.debug("Received C2B confirmation callback")

            processor.process_c2b_confirmation(payload)

            event_key, created = enqueue_callback("c2b_confirmation", payload)
            logger.info("C2B confirmation callback durably accepted", extra={"event_key": event_key, "outbox_created": created})

            status = 200
            response = jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), status
            WebhookMetrics.record_request(status, time.time() - started)
            return response

        except Exception as e:
            logger.error("Webhook confirmation error: %s", str(e))
            status = 500
            response = jsonify({"status": "error"}), status
            WebhookMetrics.record_request(status, time.time() - started)
            return response

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
            if not validate_b2c_payload(payload):
                get_metrics_collector().record_validation_failure("b2c_result")
                return jsonify({"status": "error", "error": "invalid_b2c_payload"}), 400
            try:
                _verify_request_signature(payload)
            except ValueError as exc:
                _blocked_webhook_context(payload, str(exc))
                return jsonify({"status": "error", "error": "unauthorized"}), 401

            logger.debug("Received B2C result callback")
            processor.process_b2c_result(payload)
            event_key, created = enqueue_callback("b2c_result", payload)
            logger.info("B2C callback durably accepted", extra={"event_key": event_key, "outbox_created": created})
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
            if not validate_stk_payload(payload):
                get_metrics_collector().record_validation_failure("stk_callback")
                return jsonify({"ResultCode": 1, "ResultDesc": "Invalid STK callback payload"}), 400
            try:
                _verify_request_signature(payload)
            except ValueError as exc:
                _blocked_webhook_context(payload, str(exc))
                return jsonify({"ResultCode": 1, "ResultDesc": "Unauthorized"}), 401

            logger.debug("Received STK Push callback")
            processor.process_stk_callback(payload)
            event_key, created = enqueue_callback("stk_callback", payload)
            logger.info("STK callback durably accepted", extra={"event_key": event_key, "outbox_created": created})
            return jsonify({"ResultCode": 0, "ResultDesc": "STK callback received"}), 200

        except Exception as e:
            logger.error("STK callback error: %s", str(e))
            return jsonify({"status": "error"}), 500

    @app.route("/health", methods=["GET"])
    def health_check():
        delivery_backend = "postgres_outbox"
        return (
            jsonify(
                {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "service": "mpesa-webhook-receiver",
                    "delivery_backend": delivery_backend,
                    "delivery_guarantee": "at_least_once_with_durable_outbox",
                }
            ),
            200,
        )

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
