"""Validation tests for the supported callback families."""

from ingestion.webhook_receiver import validate_b2c_payload, validate_stk_payload


def test_valid_b2c_result_payload():
    assert validate_b2c_payload({
        "Result": {
            "ResultCode": 0,
            "ResultDesc": "The service request is processed successfully.",
            "ConversationID": "AG_123",
            "OriginatorConversationID": "123456-789",
        }
    })


def test_b2c_result_requires_provider_result_structure():
    assert not validate_b2c_payload({"ResultCode": 0, "ConversationID": "AG_123"})
    assert not validate_b2c_payload({"Result": {"ResultCode": "not-a-code", "ResultDesc": "x", "ConversationID": "AG_123"}})


def test_valid_stk_callback_payload():
    assert validate_stk_payload({
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "29115-34620561-1",
                "CheckoutRequestID": "ws_CO_123",
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "CallbackMetadata": {"Item": [{"Name": "Amount", "Value": 500}],
                },
            }
        }
    })


def test_stk_callback_requires_request_ids_and_numeric_result():
    assert not validate_stk_payload({"Body": {"stkCallback": {"ResultCode": 0}}})
    assert not validate_stk_payload({
        "Body": {"stkCallback": {
            "MerchantRequestID": "m1",
            "CheckoutRequestID": "c1",
            "ResultCode": "success",
            "ResultDesc": "done",
        }}
    })



def test_b2c_route_validates_and_enqueues_callback(monkeypatch):
    import ingestion.webhook_receiver as receiver

    calls = []
    monkeypatch.setattr(receiver, "enqueue_callback", lambda event_type, payload: (calls.append((event_type, payload)) or ("key", True)))
    client = receiver.create_app().test_client()
    response = client.post("/webhook/b2c/result", json={
        "Result": {
            "ResultCode": 0,
            "ResultDesc": "Processed",
            "ConversationID": "AG_ROUTE_1",
            "OriginatorConversationID": "ORIG_1",
        }
    })

    assert response.status_code == 200
    assert len(calls) == 1
    assert calls[0][0] == "b2c_result"


def test_stk_route_rejects_malformed_callback_without_enqueue(monkeypatch):
    import ingestion.webhook_receiver as receiver

    calls = []
    monkeypatch.setattr(receiver, "enqueue_callback", lambda *args, **kwargs: calls.append(args))
    client = receiver.create_app().test_client()
    response = client.post("/webhook/stk/callback", json={"Body": {"stkCallback": {"ResultCode": 0}}})

    assert response.status_code == 400
    assert calls == []



def test_phone_masking_keeps_only_last_three_digits_for_logs():
    from ingestion.webhook_receiver import _mask_phone

    assert _mask_phone("254712345678") == "*********678"
    assert _mask_phone(None) == "unknown"



def test_distributed_rate_limiter_uses_shared_redis_counter(monkeypatch):
    import ingestion.webhook_receiver as receiver

    class FakeRedis:
        def __init__(self):
            self.values = {}
            self.expirations = {}

        def incr(self, key):
            self.values[key] = self.values.get(key, 0) + 1
            return self.values[key]

        def expire(self, key, seconds):
            self.expirations[key] = seconds
            return True

    fake_redis = FakeRedis()
    monkeypatch.setenv("REDIS_URL", "redis://fake/2")
    monkeypatch.setenv("RATE_LIMIT_PER_MIN", "1")
    monkeypatch.setattr(receiver.Redis, "from_url", lambda *args, **kwargs: fake_redis)
    monkeypatch.setattr(receiver, "enqueue_callback", lambda *args, **kwargs: ("test-key", True))
    client = receiver.create_app().test_client()
    payload = {
        "Result": {
            "ResultCode": 0,
            "ResultDesc": "Processed",
            "ConversationID": "CONVERSATION-SENSITIVE-123",
            "OriginatorConversationID": "ORIGINATOR-SENSITIVE-456",
        }
    }

    first = client.post("/webhook/b2c/result", json=payload)
    second = client.post("/webhook/b2c/result", json=payload)

    assert first.status_code == 200
    assert second.status_code == 429
    assert len(fake_redis.values) == 1
    assert next(iter(fake_redis.expirations.values())) == 60


def test_b2c_application_logs_do_not_include_conversation_ids_or_descriptions(caplog):
    import logging
    from ingestion.webhook_receiver import WebhookProcessor

    payload = {
        "Result": {
            "ResultCode": 0,
            "ResultDesc": "CUSTOMER_PRIVATE_RESULT_DESCRIPTION",
            "ConversationID": "CUSTOMER_PRIVATE_CONVERSATION_ID",
        }
    }
    with caplog.at_level(logging.INFO):
        WebhookProcessor().process_b2c_result(payload)

    assert "CUSTOMER_PRIVATE_RESULT_DESCRIPTION" not in caplog.text
    assert "CUSTOMER_PRIVATE_CONVERSATION_ID" not in caplog.text



def test_configured_redis_outage_fails_closed_for_rate_limited_route(monkeypatch):
    import ingestion.webhook_receiver as receiver

    class UnavailableRedis:
        def incr(self, _key):
            raise ConnectionError("synthetic Redis outage")

    monkeypatch.setenv("REDIS_URL", "redis://fake/2")
    monkeypatch.setenv("RATE_LIMIT_PER_MIN", "10")
    monkeypatch.setattr(receiver.Redis, "from_url", lambda *args, **kwargs: UnavailableRedis())
    client = receiver.create_app().test_client()
    response = client.post("/webhook/b2c/result", json={
        "Result": {
            "ResultCode": 0,
            "ResultDesc": "Processed",
            "ConversationID": "SYNTHETIC-CONVERSATION",
            "OriginatorConversationID": "SYNTHETIC-ORIGINATOR",
        }
    })
    assert response.status_code == 429
