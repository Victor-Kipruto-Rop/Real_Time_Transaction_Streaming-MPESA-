# Analytics Metrics Service

**Priority:** High

**Design responsibility:** Calculate reconciliation rates, transaction trends, discrepancy summaries and operational/business indicators.

**Purpose:** Produce tenant-scoped operational/business aggregates for ingestion, reconciliation, data quality and risk outcomes.

## Contract
- **Inputs:** Approved domain events and curated analytical tables.
- **Outputs:** Versioned aggregates and analytical datasets consumed through Java-authorized APIs.
- **Owns:** Derived models, aggregate definitions, lineage and refresh metadata.
- **Must not own:** Frontend/dashboard ownership, canonical transaction writes, Go's infrastructure monitoring or ungoverned raw data lake.
- **Dependencies:** Read-only analytical source, dbt or equivalent transforms, scheduler, access policy and telemetry.

## Reliability and security
Incremental refresh checkpoints, freshness indicators, late-data correction, tenant-scoped queries and explicit stale-data status.

Every event-driven handler must validate the trusted tenant envelope and schema version, use stable event IDs and durable idempotency, attach correlation/trace context, minimize sensitive fields, and support a durable dead-letter/quarantine path with controlled replay. Authenticate service calls with workload identity or short-lived credentials; use explicit timeouts, bounded concurrency and retry budgets. Keep secrets out of source control.

## Acceptance tests
Aggregate/source reconciliation, tenant filter negatives, freshness alerts, late-arrival correction, access control and PII minimization.

## Build readiness
This is the approved design boundary, not an implemented service. Before implementation, agree the API/event schemas with other platform owners, document schema/migration ownership and SLOs, add threat model and runbook, then build the package, tests, container and CI workflow together.
