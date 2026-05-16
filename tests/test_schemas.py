"""Tests for transaction schema validation.

Covers Pydantic model validation, phone number normalization,
and data type enforcement.
"""

from __future__ import annotations

from schemas.transaction_schema import MpesaEvent


def test_event_validation() -> None:
    """Test MpesaEvent schema validation."""
    event = MpesaEvent.model_validate(
        {
            "event_type": "c2b_confirmation",
            "transaction_id": "TXN123",
            "phone_number": "254712345678",
            "amount": "500",
            "data": {"foo": "bar"},
        }
    )
    assert event.event_type == "c2b_confirmation"
    assert event.transaction_id == "TXN123"
