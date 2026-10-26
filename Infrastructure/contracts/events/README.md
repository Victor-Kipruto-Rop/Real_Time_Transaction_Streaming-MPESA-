# PesaGuard Event Contracts

This directory contains versioned schemas intended for events shared between the Python streaming subsystem and PesaGuard Java/Python services.

## Rules

- Every event has a stable event name and schema version.
- Event IDs are stable across retries; a retry must not create a new business event identity.
- Consumers must be idempotent and must validate schema versions.
- Tenant context must be derived from trusted service-side resolution before publication.
- Never include secrets, raw credentials, access tokens or unnecessary personal data.
- Money must be represented as a decimal string or integer minor units, with currency explicit.
- Schema changes must be reviewed for backward compatibility and tested against all known consumers.
- Do not publish events containing fabricated provider data or claim that a callback proves settlement.

## Initial event lifecycle

1. `mpesa.callback.accepted.v1`: ingestion has validated and durably accepted a callback according to the configured acceptance policy.
2. `transaction.normalized.v1`: provider fields have been mapped to the canonical event shape.
3. `reconciliation.requested.v1`: a canonical transaction owner has been asked to evaluate ledger matching.
4. `transaction.processing.failed.v1`: processing failed and requires retry or controlled dead-letter recovery.

These are contract proposals. Before enabling production publication, compare them with existing topics and consumers and either adopt compatible names or publish a migration plan. Do not create parallel topics that carry duplicate business meaning.
