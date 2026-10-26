# Data Quality Service

**Role:** validate event schemas, semantic rules and cross-record consistency; create durable quality findings and quarantine invalid records for controlled recovery.

## Responsibilities
- Validate versioned event and record schemas.
- Check identifiers, amount/currency precision, timestamps, source references and field consistency.
- Apply versioned rules and report rule IDs, severity, evidence references and correlation IDs.
- Quarantine invalid records durably and support safe replay after correction.
- Publish quality metrics without leaking sensitive data.

## Boundaries
- Does not own provider callback authentication, canonical ledger state, reconciliation outcomes or risk scoring.
- Does not silently drop malformed messages.
- Does not log full payment payloads, secrets or unmasked personal identifiers.

## Required tests
Schema compatibility, boundary values, invalid timestamps, decimal precision, missing fields, duplicate IDs, tenant spoofing, poison-message recovery, quarantine replay and PII-safe logs.

Existing validator code remains in `Python/data_quality/` during staged extraction. This directory defines the target boundary.
