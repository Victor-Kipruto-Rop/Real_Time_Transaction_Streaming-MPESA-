"""Stable event identities for callback-level replay prevention.

Transaction identity and callback-event identity are different: a C2B validation
and its later confirmation can refer to the same transaction while remaining
distinct events.
"""

import hashlib
import json
from typing import Any, Dict


def canonical_payload(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True, default=str)


def event_identity(payload: Dict[str, Any], event_type: str) -> str:
    """Build a stable identity scoped to a callback type."""
    transaction_id = str(payload.get("TransID") or payload.get("transaction_id") or "").strip()
    if event_type in {"c2b_validation", "c2b_confirmation"} and transaction_id:
        return f"{event_type}:transaction:{transaction_id}"

    if event_type == "b2c_result":
        result_id = str(
            payload.get("ConversationID")
            or payload.get("OriginatorConversationID")
            or ""
        ).strip()
        if result_id:
            return f"{event_type}:conversation:{result_id}"

    if event_type == "stk_callback":
        body = payload.get("Body") or {}
        callback = body.get("stkCallback") or {}
        request_id = str(
            callback.get("CheckoutRequestID")
            or callback.get("MerchantRequestID")
            or ""
        ).strip()
        if request_id:
            return f"{event_type}:request:{request_id}"

    payload_hash = hashlib.sha256(canonical_payload(payload).encode("utf-8")).hexdigest()
    return f"{event_type}:payload:{payload_hash}"


def replay_key(payload: Dict[str, Any], event_type: str) -> str:
    return hashlib.sha256(event_identity(payload, event_type).encode("utf-8")).hexdigest()
