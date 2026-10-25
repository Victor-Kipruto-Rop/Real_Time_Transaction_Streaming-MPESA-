"""Callback event identity regression tests."""

from ingestion.event_identity import event_identity, replay_key


def test_c2b_validation_and_confirmation_are_distinct_events():
    payload = {"TransID": "TX123", "TransAmount": "500"}

    assert event_identity(payload, "c2b_validation") != event_identity(
        payload, "c2b_confirmation"
    )


def test_c2b_event_identity_is_stable_when_payload_changes():
    first = {"TransID": "TX123", "TransAmount": "500"}
    altered = {"TransID": "TX123", "TransAmount": "900"}

    assert replay_key(first, "c2b_confirmation") == replay_key(
        altered, "c2b_confirmation"
    )


def test_events_without_provider_ids_fall_back_to_payload_hash():
    first = {"Result": {"ResultCode": 0}}
    second = {"Result": {"ResultCode": 1}}

    assert replay_key(first, "b2c_result") != replay_key(second, "b2c_result")


def test_stk_identity_uses_checkout_request_id():
    first = {"Body": {"stkCallback": {"CheckoutRequestID": "ws_CO_123", "ResultCode": 0}}}
    retry = {"Body": {"stkCallback": {"CheckoutRequestID": "ws_CO_123", "ResultCode": 1}}}

    assert replay_key(first, "stk_callback") == replay_key(retry, "stk_callback")
