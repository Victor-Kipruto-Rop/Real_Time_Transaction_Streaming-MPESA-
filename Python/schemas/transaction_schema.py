"""Pydantic schemas for M-Pesa transaction data validation.

Defines request/response models for C2B (customer to business),
B2C (business to customer), and internal event processing.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator


def normalize_ke_phone(phone: str) -> str:
    """Normalize Kenyan phone number to international format (254XXXXXXXXX).

    Args:
        phone: Phone number in any format (+254..., 0..., 254...)

    Returns:
        Normalized phone number as string (254XXXXXXXXX)
    """
    value = (phone or "").strip().replace(" ", "").replace("-", "")
    if value.startswith("+"):
        value = value[1:]
    if value.startswith("0"):
        value = "254" + value[1:]
    if not re.fullmatch(r"254\d{9}", value):
        raise ValueError(
            "Invalid Kenyan phone number (expected 254XXXXXXXXX or 07XXXXXXXX)"
        )
    return value


class C2BValidationPayload(BaseModel):
    """C2B validation request payload from Safaricom Daraja API.

    This is the initial validation callback when a customer initiates payment.
    """

    TransID: str
    TransAmount: str
    MSISDN: str
    AccountReference: Optional[str] = None
    TransTime: Optional[str] = None

    @field_validator("MSISDN")
    @classmethod
    def _v_msisdn(cls, v: str) -> str:
        return normalize_ke_phone(v)


class C2BConfirmationPayload(C2BValidationPayload):
    """C2B confirmation callback after successful payment settlement.

    Contains full transaction details and account balances.
    """

    TransTime: str


class C2BValidationRequest(BaseModel):
    """Request schema for C2B validation/confirmation callbacks.

    Safaricom delivers a compact callback payload with a transaction ID,
    amount, phone number, and timestamp. Some payloads include optional
    account and billing fields, but the strict Daraja fields are not always
    present in the same shape across callback variants.
    """

    TransID: str
    TransAmount: str | float
    MSISDN: str
    TransTime: Optional[str] = None
    AccountReference: Optional[str] = None
    BillRefNumber: Optional[str] = None
    InvoiceNumber: Optional[str] = None
    TransactionType: Optional[str] = None
    BusinessShortCode: Optional[str] = None
    FirstName: Optional[str] = None
    MiddleName: Optional[str] = None
    LastName: Optional[str] = None
    OrgAccountBalance: Optional[str] = None

    @field_validator("MSISDN")
    @classmethod
    def _v_phone(cls, v: str) -> str:
        return normalize_ke_phone(v)

    @field_validator("TransAmount")
    @classmethod
    def _v_amount(cls, v: str | float) -> str | float:
        try:
            amount = float(v)
        except (TypeError, ValueError):
            raise ValueError("TransAmount must be numeric") from None
        if amount < 1:
            raise ValueError("Amount must be at least 1 KES")
        if amount > 1_000_000:
            raise ValueError("Amount exceeds maximum limit (1M KES)")
        return v

    @field_validator("TransTime")
    @classmethod
    def _v_time(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        datetime.strptime(str(v), "%Y%m%d%H%M%S")
        return v


class C2BConfirmationRequest(C2BValidationRequest):
    """Request schema for C2B confirmation endpoint.

    The confirmation callback shares the same data contract as validation
    but may omit some optional fields that are not always present.
    """

    pass


class B2CResultPayload(BaseModel):
    """B2C result callback for business-to-customer payouts.

    Contains payout result, balance, and transaction reference.
    """

    ConversationID: Optional[str] = None
    Result: Dict[str, Any] = Field(default_factory=dict)


EventType = Literal[
    "c2b_validation", "c2b_confirmation", "b2c_result", "stk_callback", "fraud_alert"
]


class MpesaEvent(BaseModel):
    """Internal normalized M-Pesa transaction event.

    Used internally for Kafka publishing and database storage.
    Includes full transaction context for downstream processing.
    """

    event_type: EventType
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "daraja_webhook"
    transaction_id: Optional[str] = None
    phone_number: Optional[str] = None
    amount: Optional[str] = None
    account_reference: Optional[str] = None
    transaction_time: Optional[str] = None  # Daraja format: YYYYMMDDHHmmss
    data: Dict[str, Any] = Field(default_factory=dict)
