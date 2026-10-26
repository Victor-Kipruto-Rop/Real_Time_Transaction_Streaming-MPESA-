# Feature Engineering Service

**Priority:** High

**Design responsibility:** Prepare validated, versioned, point-in-time-correct features for risk models and anomaly detection.

**Purpose:** Build validated, versioned, point-in-time-correct features for risk scoring and model evaluation.

## Contract
- **Inputs:** Validated transaction events, curated aggregates, feature definitions and point-in-time source data.
- **Outputs:** Versioned feature records/vectors, metadata, lineage and freshness signals.
- **Owns:** Feature definitions, transform versions, lineage and feature freshness metadata.
- **Must not own:** Risk decisions, canonical ledger, unapproved enrichment or customer-facing analytics.
- **Dependencies:** Curated source, data-quality rules, feature storage/registry, batch/stream processing and contracts.

## Reliability and security
Point-in-time correctness, deterministic transforms, freshness thresholds, explicit missing-value policy and backward-compatible feature versions.

Every event-driven handler must validate the trusted tenant envelope and schema version, use stable event IDs and durable idempotency, attach correlation/trace context, minimize sensitive fields, and support a durable dead-letter/quarantine path with controlled replay. Authenticate service calls with workload identity or short-lived credentials; use explicit timeouts, bounded concurrency and retry budgets. Keep secrets out of source control.

## Acceptance tests
Leakage checks, point-in-time joins, repeatability, null/outlier handling, schema evolution, tenant isolation and online/offline parity where applicable.

## Build readiness
This is the approved design boundary, not an implemented service. Before implementation, agree the API/event schemas with other platform owners, document schema/migration ownership and SLOs, add threat model and runbook, then build the package, tests, container and CI workflow together.
