"""FastAPI contract layer for local M-Pesa workflow validation.

The streaming pipeline's production ingress is the Flask webhook receiver in
``ingestion.webhook_receiver``.  This module provides the versioned API surface
used by E2E/security tests and local operators without requiring live Daraja,
Kafka, or Postgres credentials.
"""

from __future__ import annotations

import hmac
import json
import re
import threading
import uuid
from collections import defaultdict
from datetime import date, datetime, timezone
from hashlib import sha256
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field, field_validator

from app.config import settings
from schemas.transaction_schema import normalize_ke_phone


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

_STATE_LOCK = threading.RLock()
_TRANSACTIONS: Dict[str, Dict[str, Any]] = {}
_STK_TRANSACTIONS: Dict[str, Dict[str, Any]] = {}
_FRAUD_ALERTS: List[Dict[str, Any]] = []
_RECONCILIATIONS: Dict[str, Dict[str, Any]] = {}
_RATE_COUNTERS: Dict[str, int] = defaultdict(int)


class STKInitiationRequest(BaseModel):
    phone_number: str
    amount: float
    account_reference: str = Field(min_length=1, max_length=64)
    description: str = "Payment"

    @field_validator("phone_number")
    @classmethod
    def _valid_phone(cls, value: str) -> str:
        return normalize_ke_phone(value)

    @field_validator("amount")
    @classmethod
    def _valid_amount(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("amount must be greater than zero")
        if value > 1_000_000:
            raise ValueError("amount exceeds maximum limit")
        return value

    @field_validator("account_reference", "description")
    @classmethod
    def _safe_text(cls, value: str) -> str:
        if re.search(r"<\s*script|onerror\s*=", value, re.IGNORECASE):
            raise ValueError("unsafe text content")
        return value.strip()


class ReconciliationRequest(BaseModel):
    date: date
    manual: bool = False


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    return response


def _json_for_signature(payload: Dict[str, Any]) -> str:
    return json.dumps(payload)


def _verify_signature(payload: Dict[str, Any], signature: Optional[str]) -> None:
    if not signature:
        raise HTTPException(status_code=401, detail="missing signature")
    secret = getattr(settings, "WEBHOOK_SIGNING_SECRET", "") or "test-secret"
    expected = hmac.new(
        secret.encode(),
        _json_for_signature(payload).encode(),
        sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=403, detail="invalid signature")


def _validate_query_phone(phone_number: Optional[str]) -> Optional[str]:
    if phone_number is None:
        return None
    try:
        return normalize_ke_phone(phone_number)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _validate_query_date(value: Optional[str], name: str) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"invalid {name}") from exc


def _transaction_from_c2b(
    payload: Dict[str, Any], status: str = "success"
) -> Dict[str, Any]:
    phone = normalize_ke_phone(str(payload.get("MSISDN", "")))
    amount = float(payload.get("TransAmount", 0))
    if amount <= 0 or amount > 1_000_000:
        raise HTTPException(status_code=422, detail="invalid amount")
    trans_time = str(
        payload.get("TransTime") or datetime.now().strftime("%Y%m%d%H%M%S")
    )
    datetime.strptime(trans_time, "%Y%m%d%H%M%S")
    transaction_id = str(payload.get("TransID") or uuid.uuid4().hex)
    return {
        "transaction_id": transaction_id,
        "phone_number": phone,
        "amount": amount,
        "status": status,
        "account_reference": str(payload.get("BillRefNumber") or ""),
        "transaction_time": trans_time,
        "source": "c2b_confirmation",
        "received_at": datetime.now(timezone.utc).isoformat(),
    }


def _customer_transactions(phone_number: str) -> List[Dict[str, Any]]:
    return [
        txn for txn in _TRANSACTIONS.values() if txn["phone_number"] == phone_number
    ]


def _risk_profile(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    count = len(transactions)
    total = sum(float(txn["amount"]) for txn in transactions)
    max_amount = max((float(txn["amount"]) for txn in transactions), default=0)
    fraud_score = 0.1
    if count >= 10 and max_amount >= 50_000:
        fraud_score = 0.9
    elif max_amount >= 100_000:
        fraud_score = 0.7
    elif total >= 250_000:
        fraud_score = 0.6
    return {
        "fraud_score": fraud_score,
        "risk_level": "high" if fraud_score >= 0.7 else "low",
    }


def _record_fraud_if_needed(phone_number: str) -> None:
    transactions = _customer_transactions(phone_number)
    profile = _risk_profile(transactions)
    if profile["fraud_score"] < 0.7:
        return
    alert_id = f"fraud-{phone_number}"
    if any(alert["alert_id"] == alert_id for alert in _FRAUD_ALERTS):
        return
    _FRAUD_ALERTS.append(
        {
            "alert_id": alert_id,
            "phone_number": phone_number,
            "severity": "high",
            "fraud_score": profile["fraud_score"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )


@app.get("/api/v1/health")
async def api_health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "mpesa-api",
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/v1/transactions/initiate-stk")
async def initiate_stk(payload: STKInitiationRequest) -> Dict[str, Any]:
    checkout_id = f"ws_CO_{uuid.uuid4().hex[:24]}"
    transaction = {
        "checkout_request_id": checkout_id,
        "phone_number": payload.phone_number,
        "amount": payload.amount,
        "account_reference": payload.account_reference,
        "description": payload.description,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with _STATE_LOCK:
        _STK_TRANSACTIONS[checkout_id] = transaction
    return {"status": "pending", "checkout_request_id": checkout_id}


@app.get("/api/v1/transactions/stk/{checkout_request_id}/status")
async def stk_status(checkout_request_id: str) -> Dict[str, Any]:
    with _STATE_LOCK:
        transaction = _STK_TRANSACTIONS.get(checkout_request_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="transaction not found")
    return transaction


@app.post("/api/v1/webhooks/stk/callback")
async def stk_callback(
    payload: Dict[str, Any],
    x_safaricom_signature: Optional[str] = Header(None),
) -> Dict[str, Any]:
    _verify_signature(payload, x_safaricom_signature)
    callback = payload.get("Body", {}).get("stkCallback", {})
    checkout_id = callback.get("CheckoutRequestID")
    result_code = int(callback.get("ResultCode", -1))
    status = "success" if result_code == 0 else "failed"
    if not checkout_id:
        raise HTTPException(status_code=422, detail="missing checkout request id")

    with _STATE_LOCK:
        stk_txn = _STK_TRANSACTIONS.get(checkout_id, {})
        stk_txn.update({"checkout_request_id": checkout_id, "status": status})
        _STK_TRANSACTIONS[checkout_id] = stk_txn
        if status == "success":
            txn_id = callback.get("MpesaReceiptNumber") or checkout_id
            _TRANSACTIONS[txn_id] = {
                "transaction_id": txn_id,
                "phone_number": stk_txn.get("phone_number", ""),
                "amount": stk_txn.get("amount", 0),
                "status": "success",
                "account_reference": stk_txn.get("account_reference", ""),
                "transaction_time": datetime.now().strftime("%Y%m%d%H%M%S"),
                "source": "stk_callback",
                "received_at": datetime.now(timezone.utc).isoformat(),
            }
    return {"ResultCode": 0, "ResultDesc": "accepted"}


@app.post("/api/v1/webhooks/c2b/validation")
async def c2b_validation(
    payload: Dict[str, Any],
    x_safaricom_signature: Optional[str] = Header(None),
) -> Dict[str, Any]:
    _verify_signature(payload, x_safaricom_signature)
    _transaction_from_c2b(payload, status="validated")
    return {"ResultCode": 0, "ResultDesc": "Validation accepted"}


@app.post("/api/v1/webhooks/c2b/confirmation")
async def c2b_confirmation(
    payload: Dict[str, Any],
    x_safaricom_signature: Optional[str] = Header(None),
) -> Dict[str, Any]:
    _verify_signature(payload, x_safaricom_signature)
    transaction = _transaction_from_c2b(payload)
    with _STATE_LOCK:
        _TRANSACTIONS[transaction["transaction_id"]] = transaction
        _record_fraud_if_needed(transaction["phone_number"])
    return {"ResultCode": 0, "ResultDesc": "Confirmation accepted"}


@app.get("/api/v1/transactions")
async def list_transactions(
    phone_number: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
) -> Dict[str, Any]:
    phone = _validate_query_phone(phone_number)
    _validate_query_date(start_date, "start_date")
    _validate_query_date(end_date, "end_date")
    with _STATE_LOCK:
        data = list(_TRANSACTIONS.values())
    if phone:
        data = [txn for txn in data if txn["phone_number"] == phone]
    if status:
        data = [txn for txn in data if txn["status"] == status]
    return {"data": data[:limit], "count": min(len(data), limit)}


@app.get("/api/v1/transactions/{transaction_id}")
async def get_transaction(transaction_id: str) -> Dict[str, Any]:
    with _STATE_LOCK:
        transaction = _TRANSACTIONS.get(transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="transaction not found")
    return transaction


@app.get("/api/v1/analytics/customer/{phone_number}")
async def customer_analytics(phone_number: str) -> Dict[str, Any]:
    phone = _validate_query_phone(phone_number) or phone_number
    with _STATE_LOCK:
        transactions = _customer_transactions(phone)
    total = sum(float(txn["amount"]) for txn in transactions)
    return {
        "phone_number": phone,
        "profile": {
            "transaction_count": len(transactions),
            "total_amount": total,
        },
        "risk_profile": _risk_profile(transactions),
    }


@app.get("/api/v1/analytics/summary")
async def analytics_summary() -> Dict[str, Any]:
    with _STATE_LOCK:
        transactions = list(_TRANSACTIONS.values())
    total = sum(float(txn["amount"]) for txn in transactions)
    return {
        "transaction_count": len(transactions),
        "total_amount": total,
        "unique_customers": len({txn["phone_number"] for txn in transactions}),
    }


@app.get("/api/v1/analytics/fraud-alerts")
async def fraud_alerts(severity: Optional[str] = None) -> Dict[str, Any]:
    with _STATE_LOCK:
        alerts = list(_FRAUD_ALERTS)
    if severity:
        alerts = [alert for alert in alerts if alert["severity"] == severity]
    return {"data": alerts, "count": len(alerts)}


@app.post("/api/v1/reconciliation/daily")
async def daily_reconciliation(
    payload: ReconciliationRequest, response: Response
) -> Dict[str, Any]:
    reconciliation_id = f"recon-{payload.date.isoformat()}-{uuid.uuid4().hex[:8]}"
    with _STATE_LOCK:
        total = len(_TRANSACTIONS)
        record = {
            "reconciliation_id": reconciliation_id,
            "status": "completed",
            "date": payload.date.isoformat(),
            "manual": payload.manual,
            "statistics": {
                "matched": total,
                "unmatched": 0,
                "match_rate": 1.0,
            },
        }
        _RECONCILIATIONS[reconciliation_id] = record
    response.status_code = 200
    return record


@app.get("/api/v1/reconciliation/{reconciliation_id}")
async def get_reconciliation(reconciliation_id: str) -> Dict[str, Any]:
    with _STATE_LOCK:
        record = _RECONCILIATIONS.get(reconciliation_id)
    if not record:
        raise HTTPException(status_code=404, detail="reconciliation not found")
    return record


@app.get("/api/v1/admin/logs")
async def admin_logs() -> Dict[str, Any]:
    raise HTTPException(status_code=401, detail="authentication required")
