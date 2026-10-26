# Reconciliation Engine

**Role:** match normalized provider transaction records against the authoritative ledger interface and classify discrepancies.

## Outcomes
- matched
- unmatched_provider_record
- unmatched_ledger_record
- amount_mismatch
- currency_mismatch
- reference_mismatch
- duplicate_candidate
- ambiguous_match
- pending_late_arrival
- review_required

Each outcome should include deterministic rule/version metadata, reason codes, source record references, evaluation timestamp and correlation ID.

## Boundaries
- Java owns canonical transaction-domain APIs and state. Use its authorized ledger API/read model; do not create a competing ledger.
- Risk scoring supplies signals; it does not decide reconciliation outcomes.
- No payment initiation, confirmation, refund, reversal, settlement or money movement.
- Never resolve ambiguous matches by discarding evidence.

## Required tests
Exact matches, partial matches, duplicate events, missing records on either side, amount/currency mismatch, timezone tolerance, late arrivals, reordered events, replay determinism, tenant isolation, concurrent duplicate work and upstream timeouts.

Implementation is to be extracted from existing analytics/streaming code after dependency and ownership checks. This README defines the target boundary, not a claim of completed migration.
