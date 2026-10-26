"""Layered fraud and anomaly risk engine for transaction decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import math
from statistics import mean, pstdev
from typing import Any, Iterable, Mapping, Sequence

MODEL_VERSION = "fraud-rules-v2"
RISK_LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")


@dataclass(frozen=True)
class FraudFeatures:
    transaction_frequency: float
    amount_deviation: float
    velocity: float
    customer_history: float
    tenant_baseline: float
    time_pattern: float
    amount: float
    customer_id: str
    merchant_id: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "transaction_frequency": self.transaction_frequency,
            "amount_deviation": self.amount_deviation,
            "velocity": self.velocity,
            "customer_history": self.customer_history,
            "tenant_baseline": self.tenant_baseline,
            "time_pattern": self.time_pattern,
            "amount": self.amount,
            "customer_id": self.customer_id,
            "merchant_id": self.merchant_id,
        }


@dataclass(frozen=True)
class RuleResult:
    code: str
    triggered: bool
    weight: float
    reason: str


@dataclass(frozen=True)
class RiskDecision:
    risk_score: float
    risk_level: str
    action: str
    reason_codes: tuple[str, ...]
    model_version: str
    rules_triggered: tuple[str, ...]
    features: FraudFeatures
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_dict(self) -> dict[str, Any]:
        return {
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "action": self.action,
            "reason_codes": list(self.reason_codes),
            "model_version": self.model_version,
            "rules_triggered": list(self.rules_triggered),
            "features": self.features.as_dict(),
            "detected_at": self.detected_at.isoformat(),
        }


def _number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return number if math.isfinite(number) else default


def _timestamp(transaction: Mapping[str, Any]) -> datetime | None:
    value = transaction.get("TransTime") or transaction.get("timestamp") or transaction.get("created_at")
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value or "").strip()
    if len(text) == 14 and text.isdigit():
        try:
            return datetime.strptime(text, "%Y%m%d%H%M%S").replace(tzinfo=ZoneInfo("Africa/Nairobi"))
        except ValueError:
            return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _identity(transaction: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = str(transaction.get(key) or "").strip()
        if value:
            return value
    return "unknown"


def detect_cumulative_subthreshold_activity(transaction: Mapping[str, Any], history: Sequence[Mapping[str, Any]] = (), *, threshold: float, window_seconds: int = 3600, min_transactions: int = 3) -> dict[str, Any]:
    """Screen for cumulative below-threshold activity using tenant-scoped history.

    This produces explainable evidence for review only. It never blocks,
    reverses, or posts transactions.
    """
    try:
        limit = float(threshold)
    except (TypeError, ValueError, OverflowError):
        limit = float("nan")
    if not math.isfinite(limit) or limit < 0:
        raise ValueError("threshold must be a finite non-negative number")
    window = max(0, int(window_seconds))
    minimum = max(2, int(min_transactions))
    result = {"evaluated": False, "triggered": False, "transaction_count": 0,
              "total_amount": 0.0, "threshold": limit, "window_seconds": window,
              "reason_codes": []}
    if limit <= 0:
        result["reason_codes"] = ["threshold_not_positive"]
        return result
    customer = _identity(transaction, "MSISDN", "customer_id", "customer")
    current_id = _identity(transaction, "TransID", "trans_id", "transaction_id")
    current_time = _timestamp(transaction)
    current_amount = _number(transaction.get("TransAmount") or transaction.get("amount"), float("nan"))
    if customer == "unknown" or current_id == "unknown" or current_time is None or not math.isfinite(current_amount) or current_amount <= 0 or current_amount >= limit:
        result["reason_codes"] = ["insufficient_current_transaction_evidence"]
        return result
    observed = {current_id: (current_time, current_amount)}
    for item in history:
        item_id = _identity(item, "TransID", "trans_id", "transaction_id")
        if _identity(item, "MSISDN", "customer_id", "customer") != customer or item_id == "unknown" or item_id in observed:
            continue
        item_time = _timestamp(item)
        if item_time is None:
            continue
        age = (current_time - item_time).total_seconds()
        if age < 0 or age > window:
            continue
        item_amount = _number(item.get("TransAmount") or item.get("amount"), float("nan"))
        if not math.isfinite(item_amount) or item_amount <= 0 or item_amount >= limit:
            continue
        observed[item_id] = (item_time, item_amount)
    total = sum(amount for _, amount in observed.values())
    count = len(observed)
    triggered = count >= minimum and total >= limit
    return {"evaluated": True, "triggered": triggered, "transaction_count": count,
            "total_amount": round(total, 2), "threshold": limit, "window_seconds": window,
            "reason_codes": ["cumulative_subthreshold_activity"] if triggered else []}


def calculate_features(
    transaction: Mapping[str, Any],
    history: Sequence[Mapping[str, Any]] = (),
    tenant_baseline: Mapping[str, Any] | None = None,
) -> FraudFeatures:
    """Calculate bounded, explainable features from transaction and tenant context."""
    baseline = tenant_baseline or {}
    amount = _number(transaction.get("TransAmount") or transaction.get("amount"))
    customer_id = _identity(transaction, "MSISDN", "customer_id", "customer")
    merchant_id = _identity(transaction, "BusinessShortCode", "merchant_id", "merchant")
    customer_history = [item for item in history if _identity(item, "MSISDN", "customer_id", "customer") == customer_id]
    tenant_amounts = [_number(item.get("TransAmount") or item.get("amount")) for item in history]
    tenant_amounts = [value for value in tenant_amounts if value > 0]
    customer_times = [_timestamp(item) for item in customer_history]
    current_time = _timestamp(transaction)
    recent_customer = [value for value in customer_times if current_time and value and 0 <= (current_time - value).total_seconds() <= 3600]
    frequency = len(recent_customer) / 60.0
    velocity = len([value for value in recent_customer if (current_time - value).total_seconds() <= 60]) if current_time else 0.0
    mean_amount = _number(baseline.get("mean_amount"), mean(tenant_amounts) if tenant_amounts else amount)
    std_amount = _number(baseline.get("std_amount"), pstdev(tenant_amounts) if len(tenant_amounts) > 1 else max(mean_amount * 0.25, 1.0))
    # Use a robust median/MAD score once there is enough tenant history. This
    # prevents a few extreme transactions from inflating the mean and hiding
    # later outliers. Small samples retain the existing conservative fallback.
    try:
        from .algorithmic_intelligence import robust_amount_deviation
    except ImportError:  # pragma: no cover - top-level script execution
        from algorithmic_intelligence import robust_amount_deviation
    robust_deviation = robust_amount_deviation(amount, tenant_amounts)
    amount_deviation = (
        robust_deviation
        if robust_deviation is not None
        else min(abs(amount - mean_amount) / max(std_amount, 1.0), 5.0) / 5.0
    )
    customer_baseline = _number(baseline.get("customer_mean_amount"), mean([_number(item.get("TransAmount") or item.get("amount")) for item in customer_history]) if customer_history else mean_amount)
    customer_history_score = min(len(customer_history) / 20.0, 1.0)
    tenant_baseline_score = min(abs(amount - mean_amount) / max(mean_amount, 1.0), 5.0) / 5.0
    # Daraja's compact TransTime is East Africa Time. Convert aware ISO
    # timestamps to the same business timezone before applying local-hour rules.
    local_time = current_time.astimezone(ZoneInfo("Africa/Nairobi")) if current_time else None
    hour = local_time.hour if local_time else 12
    time_pattern = 1.0 if local_time and (hour < 5 or hour >= 23) else 0.0
    return FraudFeatures(
        transaction_frequency=min(frequency, 1.0),
        amount_deviation=amount_deviation,
        velocity=min(velocity / 5.0, 1.0),
        customer_history=customer_history_score,
        tenant_baseline=max(tenant_baseline_score, min(abs(amount - customer_baseline) / max(customer_baseline, 1.0), 5.0) / 5.0),
        time_pattern=time_pattern,
        amount=amount,
        customer_id=customer_id,
        merchant_id=merchant_id,
    )


def evaluate_rules(
    transaction: Mapping[str, Any],
    features: FraudFeatures,
    history: Sequence[Mapping[str, Any]] = (),
    *,
    amount_threshold: float = 150_000.0,
    velocity_limit: float = 5.0,
) -> tuple[RuleResult, ...]:
    transaction_id = _identity(transaction, "TransID", "trans_id", "transaction_id")
    duplicate = transaction_id != "unknown" and any(
        _identity(item, "TransID", "trans_id", "transaction_id") == transaction_id
        for item in history
    )
    amount = features.amount
    customer_id = _identity(transaction, "MSISDN", "customer_id", "customer")
    current_time = _timestamp(transaction)
    recent_customer_amounts = []
    if customer_id != "unknown" and current_time is not None:
        for item in history:
            item_customer = _identity(item, "MSISDN", "customer_id", "customer")
            item_time = _timestamp(item)
            if item_customer != customer_id or item_time is None:
                continue
            age_seconds = (current_time - item_time).total_seconds()
            if 0 <= age_seconds <= 300:
                recent_customer_amounts.append(round(_number(item.get("TransAmount") or item.get("amount")), 2))
    rapid_changes = len(set(recent_customer_amounts[-5:])) >= 4
    cumulative_activity = detect_cumulative_subthreshold_activity(transaction, history, threshold=amount_threshold)
    return (
        RuleResult("velocity", features.velocity * 5 >= velocity_limit, 0.30, "transaction velocity exceeded the configured limit"),
        RuleResult("amount_threshold", amount > amount_threshold, 0.20, "transaction amount exceeded the tenant threshold"),
        RuleResult("duplicate_activity", duplicate, 0.30, "transaction identity was already observed"),
        RuleResult("unusual_time", features.time_pattern > 0, 0.10, "transaction occurred during an unusual time window"),
        RuleResult("rapid_transaction_changes", rapid_changes, 0.15, "recent transaction amounts changed rapidly"),
        RuleResult("cumulative_subthreshold_activity", cumulative_activity["triggered"], 0.25, "distinct below-threshold transactions for the same customer reached the configured threshold in the review window"),
    )


def _risk_level(score: float) -> str:
    if score >= 0.85:
        return "CRITICAL"
    if score >= 0.65:
        return "HIGH"
    if score >= 0.35:
        return "MEDIUM"
    return "LOW"


def _action(level: str) -> str:
    return {"LOW": "process", "MEDIUM": "monitor", "HIGH": "review", "CRITICAL": "escalate"}[level]


def assess_transaction(
    transaction: Mapping[str, Any],
    history: Sequence[Mapping[str, Any]] = (),
    tenant_baseline: Mapping[str, Any] | None = None,
    *,
    model_version: str = MODEL_VERSION,
    amount_threshold: float = 150_000.0,
    velocity_limit: float = 5.0,
) -> RiskDecision:
    if not math.isfinite(float(amount_threshold)) or amount_threshold < 0:
        raise ValueError("amount_threshold must be a finite non-negative number")
    if not math.isfinite(float(velocity_limit)) or velocity_limit <= 0:
        raise ValueError("velocity_limit must be a finite positive number")
    features = calculate_features(transaction, history, tenant_baseline)
    rules = evaluate_rules(transaction, features, history, amount_threshold=amount_threshold, velocity_limit=velocity_limit)
    feature_score = (
        features.amount_deviation * 0.25
        + features.velocity * 0.25
        + features.tenant_baseline * 0.20
        + features.time_pattern * 0.10
        # Established history is context, not a reason to increase suspicion.
        # This contribution represents uncertainty for a new/unknown customer.
        + (1.0 - min(features.customer_history, 1.0)) * 0.10
    )
    rule_score = sum(rule.weight for rule in rules if rule.triggered)
    score = round(min(1.0, max(feature_score, rule_score) + min(feature_score * rule_score, 0.25)), 4)
    triggered = tuple(rule.code for rule in rules if rule.triggered)
    level = _risk_level(score)
    return RiskDecision(score, level, _action(level), triggered, model_version, triggered, features)


def persist_assessment(session: Any, tenant_id: str, transaction_id: str, decision: RiskDecision) -> Any:
    """Upsert the explainable decision for a tenant-scoped transaction."""
    from models import FraudRiskAssessment

    assessment = session.query(FraudRiskAssessment).filter_by(
        tenant_id=tenant_id,
        transaction_id=transaction_id,
    ).one_or_none()
    values = {
        "risk_score": decision.risk_score,
        "risk_level": decision.risk_level,
        "action": decision.action,
        "reason_codes": list(decision.reason_codes),
        "model_version": decision.model_version,
        "rules_triggered": list(decision.rules_triggered),
        "features": decision.features.as_dict(),
    }
    if assessment is None:
        assessment = FraudRiskAssessment(tenant_id=tenant_id, transaction_id=transaction_id, **values)
        session.add(assessment)
    else:
        for key, value in values.items():
            setattr(assessment, key, value)
    session.flush()
    return assessment


def evaluate_predictions(
    predictions: Iterable[tuple[RiskDecision, bool] | tuple[RiskDecision, bool, datetime]],
) -> dict[str, Any]:
    """Measure classification metrics and latency only when event time is supplied.

    Accepted rows are (decision, actual_fraud) or
    (decision, actual_fraud, event_time). A decision's age is not detection
    latency, so latency is left null when the source event time is unavailable.
    """
    rows = list(predictions)
    true_positive = false_positive = false_negative = true_negative = 0
    latencies: list[float] = []
    for row in rows:
        decision, actual_fraud = row[0], row[1]
        event_time = row[2] if len(row) >= 3 else None
        predicted = decision.risk_level in {"HIGH", "CRITICAL"}
        if predicted and actual_fraud:
            true_positive += 1
        elif predicted:
            false_positive += 1
        elif actual_fraud:
            false_negative += 1
        else:
            true_negative += 1
        if isinstance(event_time, datetime):
            if event_time.tzinfo is None:
                event_time = event_time.replace(tzinfo=timezone.utc)
            latency_ms = (decision.detected_at - event_time.astimezone(timezone.utc)).total_seconds() * 1000
            if latency_ms >= 0:
                latencies.append(latency_ms)
    return {
        "precision": true_positive / max(true_positive + false_positive, 1),
        "recall": true_positive / max(true_positive + false_negative, 1),
        "false_positives": float(false_positive),
        "false_negatives": float(false_negative),
        "true_negatives": float(true_negative),
        "detection_latency_ms": sum(latencies) / len(latencies) if latencies else None,
        "latency_sample_count": float(len(latencies)),
    }
