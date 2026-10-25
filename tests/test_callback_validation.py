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
