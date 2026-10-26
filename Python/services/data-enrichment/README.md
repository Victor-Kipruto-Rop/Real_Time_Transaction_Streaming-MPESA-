# Data Enrichment Service

**Purpose:** Enrich approved records with authorized reference data such as merchant classifications and configured reference lists.

## Contract
- **Inputs:** Validated references, approved source configuration and versioned reference datasets.
- **Outputs:** Enriched record plus provenance, source timestamp, quality/confidence and explicit unavailable status.
- **Owns:** Reference dataset versions, enrichment provenance, cache metadata and source health for its own integrations.
- **Must not own:** Authoritative merchant identity, KYB verification, unapproved scraping, provider credentials or fabricated fields.
- **Dependencies:** Java-owned merchant APIs, approved reference sources, cache, audit and telemetry.

## Reliability and security
Source allowlists, timeouts, bounded retries, cache TTL, circuit breakers, provenance and explicit unknown/unavailable state; never invent data.

Every event-driven handler must validate the trusted tenant envelope and schema version, use stable event IDs and durable idempotency, attach correlation/trace context, minimize sensitive fields, and support a durable dead-letter/quarantine path with controlled replay. Authenticate service calls with workload identity or short-lived credentials; use explicit timeouts, bounded concurrency and retry budgets. Keep secrets out of source control.

## Acceptance tests
Unavailable/stale source, conflicting values, tenant isolation, provenance, SSRF defense, timeout handling and sensitive-data minimization.

## Build readiness
This is the approved design boundary, not an implemented service. Before implementation, agree the API/event schemas with other platform owners, document schema/migration ownership and SLOs, add threat model and runbook, then build the package, tests, container and CI workflow together.
