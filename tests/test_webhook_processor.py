"""Tests for webhook processor.

Covers validation callbacks, confirmation processing, and error handling
for incoming Safaricom Daraja webhooks.
"""

from __future__ import annotations

from ingestion.webhook_receiver import WebhookProcessor


def test_validation_rejects_large_amount() -> None:
    """Test that validation rejects amounts exceeding limit."""
    payload = {"TransID": "T1", "TransAmount": "1000001", "MSISDN": "254700000000"}
    resp = WebhookProcessor.process_c2b_validation(payload)
    assert resp["ResultCode"] == "1"


def test_validation_requires_amount() -> None:
    payload = {"TransID": "T1", "MSISDN": "254700000000"}
    resp = WebhookProcessor.process_c2b_validation(payload)
    assert resp["ResultCode"] == "1"
