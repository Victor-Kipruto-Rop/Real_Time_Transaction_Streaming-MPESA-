"""
STK push handler for Project 01.

Responsibilities:
- Initiate STK push via Daraja client
- Validate/normalize phone numbers and amounts
- Track status in-memory for quick lookups
- Persist initiation + callbacks to Postgres
- (Optional) publish callback events to Kafka
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from schemas.transaction_schema import normalize_ke_phone

from .daraja_client import DarajaClient
from .kafka_producer import MpesaKafkaProducer

logger = logging.getLogger(__name__)


class STKStatus(str, Enum):
    """Status enum for STK push transactions."""

    INITIATED = "initiated"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class STKPushHandler:
    """Handler for Safaricom STK push payment flows.

    Manages initiation, tracking, and callback processing for STK push payments.
    """

    def __init__(self, daraja_client: DarajaClient, db_connection: Any):
        """Initialize STK push handler.

        Args:
            daraja_client: DarajaClient instance for API calls
            db_connection: Database connection for persistence
        """
        if daraja_client is None:
            raise TypeError("daraja_client is required")
        if db_connection is None:
            raise TypeError("db_connection is required")

        self.daraja_client = daraja_client
        self.db_connection = db_connection
        self._producer: Optional[MpesaKafkaProducer] = None
        self.transactions: Dict[str, Dict[str, Any]] = {}

    def attach_producer(self, producer: MpesaKafkaProducer) -> None:
        """Attach Kafka producer for publishing callbacks.

        Args:
            producer: MpesaKafkaProducer instance
        """
        self._producer = producer

    @staticmethod
    def _validate_amount(amount: int) -> None:
        if amount <= 0:
            raise ValueError("amount must be > 0")
        if amount > 1_000_000:
            raise ValueError("amount exceeds maximum limit (1M KES)")

    @staticmethod
    def _status_from_result_code(result_code: int) -> STKStatus:
        if result_code == 0:
            return STKStatus.COMPLETED
        if result_code == 1:
            return STKStatus.CANCELLED
        if result_code == 10:
            return STKStatus.EXPIRED
        return STKStatus.FAILED

    def initiate_stk_push(
        self,
        phone_number: str,
        amount: int,
        account_reference: str,
        description: str = "Payment",
    ) -> Dict[str, Any]:
        """Initiate STK push payment request.

        Args:
            phone_number: Kenyan phone number (auto-normalized)
            amount: Amount in KES (1-1,000,000)
            account_reference: Account/invoice reference
            description: Payment description

        Returns:
            API response with CheckoutRequestID
        """
        phone = normalize_ke_phone(phone_number)
        self._validate_amount(amount)

        response = self.daraja_client.initiate_stk_push(
            phone_number=phone, amount=amount, description=description
        )

        checkout_id = response.get("CheckoutRequestID") or response.get(
            "checkout_request_id"
        )
        now = datetime.now(timezone.utc).isoformat()

        if checkout_id:
            self.transactions[checkout_id] = {
                "checkout_request_id": checkout_id,
                "phone": phone,
                "amount": amount,
                "account_reference": account_reference,
                "description": description,
                "status": STKStatus.INITIATED.value,
                "initiated_at": now,
            }
            self._persist_initiation(checkout_id)

        return response

    # Backwards compatible alias used in older docs
    def initiate_push(
        self,
        phone_number: str,
        amount: int,
        description: str = "Payment",
        merchant_id: str = "MERCHANT001",
        reference_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Initiate STK push (backwards-compatible alias).

        Args:
            phone_number: Kenyan phone number
            amount: Amount in KES
            description: Payment description
            merchant_id: Merchant identifier (legacy parameter)
            reference_id: Reference ID (legacy parameter)

        Returns:
            API response with CheckoutRequestID
        """
        return self.initiate_stk_push(
            phone_number=phone_number,
            amount=amount,
            account_reference=reference_id or merchant_id,
            description=description,
        )

    def handle_callback(self, callback_payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(callback_payload, dict):
            raise ValueError("callback_payload must be a dict")

        body = callback_payload.get("Body")
        if not isinstance(body, dict):
            raise ValueError("Malformed callback: missing Body")

        stk = body.get("stkCallback")
        if not isinstance(stk, dict):
            raise ValueError("Malformed callback: missing stkCallback")

        checkout_id = stk.get("CheckoutRequestID")
        result_code = int(stk.get("ResultCode", -1))
        result_desc = stk.get("ResultDesc", "")

        checkout_key = checkout_id if isinstance(checkout_id, str) else "unknown"

        status = self._status_from_result_code(result_code).value
        now = datetime.now(timezone.utc).isoformat()

        txn = self.transactions.get(checkout_key, {})
        txn.update(
            {
                "checkout_request_id": checkout_key,
                "status": status,
                "result_code": result_code,
                "result_desc": result_desc,
                "completed_at": now,
            }
        )
        if checkout_key != "unknown":
            self.transactions[checkout_key] = txn
            self._persist_callback(checkout_key)

        if self._producer and checkout_key != "unknown":
            self._producer.publish_event(
                event={
                    "event_type": "stk_callback",
                    "checkout_request_id": checkout_key,
                    "result_code": result_code,
                    "result_desc": result_desc,
                    "transaction": txn,
                    "received_at": now,
                },
                key=txn.get("phone"),
            )

        return {
            "checkout_request_id": checkout_key,
            "status": status,
            "result_code": result_code,
        }

    def get_transaction_status(
        self, checkout_request_id: str
    ) -> Optional[Dict[str, Any]]:
        return self.transactions.get(checkout_request_id)

    def _persist_initiation(self, checkout_request_id: str) -> None:
        txn = self.transactions.get(checkout_request_id)
        if not txn:
            return
        with self.db_connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO mpesa_stk_transactions
                  (
                    checkout_request_id,
                    phone_number,
                    amount,
                    account_reference,
                    status,
                    initiated_at,
                    description
                  )
                VALUES
                  (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (checkout_request_id) DO UPDATE SET
                  status = EXCLUDED.status,
                  updated_at = NOW()
                """,
                (
                    checkout_request_id,
                    txn.get("phone"),
                    txn.get("amount"),
                    txn.get("account_reference"),
                    txn.get("status"),
                    txn.get("initiated_at"),
                    txn.get("description"),
                ),
            )
        self.db_connection.commit()

    def _persist_callback(self, checkout_request_id: str) -> None:
        txn = self.transactions.get(checkout_request_id)
        if not txn:
            return
        with self.db_connection.cursor() as cur:
            cur.execute(
                """
                UPDATE mpesa_stk_transactions
                SET status = %s,
                    result_code = %s,
                    result_desc = %s,
                    completed_at = %s,
                    updated_at = NOW()
                WHERE checkout_request_id = %s
                """,
                (
                    txn.get("status"),
                    txn.get("result_code"),
                    txn.get("result_desc"),
                    txn.get("completed_at"),
                    checkout_request_id,
                ),
            )
        self.db_connection.commit()
