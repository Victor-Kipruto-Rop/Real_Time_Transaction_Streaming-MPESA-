# TELIXO Python Service Boundaries

## Approved deployable services

Start with four Python service boundaries:

1. **Transaction Ingestion** — consume durably accepted provider events and approved imports, normalize records and emit versioned internal events.
2. **Reconciliation Engine** — deterministic matching and discrepancy classification against the canonical ledger interface.
3. **Data Quality** — schema and business-rule validation, quarantine, replay metadata and quality metrics.
4. **Risk Scoring** — explainable anomaly/risk signals with model/rule version metadata.

Streaming, batch backfills, analytics, feature engineering and model evaluation start as libraries or scheduled jobs, not always-on microservices. Split them only when independent scaling, ownership, SLOs or failure isolation justify it.

## Ownership and calls

- Java owns the API/control plane, authentication, tenant/merchant configuration and canonical transaction-domain APIs.
- Java's configured callback boundary performs provider-edge authentication and durable receipt. Python must not run a competing public callback receiver once that boundary is active.
- Python ingestion consumes accepted events from Kafka/Redpanda, validates the internal envelope, normalizes provider fields, enforces durable idempotency and emits versioned events.
- Python reconciliation uses the authorized ledger API/read model and produces matching outcomes/discrepancies. It must not create an alternative authoritative ledger.
- Python data quality validates payloads and datasets. Quarantine must be durable and replayable.
- Python risk scoring consumes approved features and returns a score, reason codes and model/rule version. It is a signal, not authorization to move funds.
- Go owns event relay, quotas and infrastructure monitoring.
- Elixir owns outbound webhooks, notifications and delivery retry orchestration.

## Event contract

Each internal event should carry `event_id`, `event_type`, `schema_version`, UTC occurrence/acceptance timestamps, `correlation_id`, trace context where available, a trusted tenant reference in a verified internal envelope, source/provider reference and a payload hash. Minimize sensitive fields.

Consumers must be idempotent and commit offsets only after durable side effects. Poison messages go to a durable DLQ/quarantine with reason, attempt count, correlation ID and replay state. Use an outbox or equivalent recovery mechanism where database state and publication must be atomic.

## Service API conventions

- Health: `/health/live` and `/health/ready`; metrics endpoints internal-only.
- Authenticate service-to-service calls with workload identity or short-lived credentials; use mTLS where supported.
- Enforce tenant scope at every boundary. Never trust client/provider-supplied tenant IDs by themselves.
- Use explicit timeouts, bounded concurrency, retry budgets and jittered exponential backoff.
- Never log credentials, tokens, full payment payloads or unmasked personal identifiers.
- Version OpenAPI/event contracts and run compatibility tests.

## Data ownership

Java owns canonical tenant and transaction-domain state. Python may own ingestion receipts, processing attempts, quality findings, reconciliation computation artifacts and model metadata under explicit schemas and retention. Each service owns its migrations; multiple services must not write the same tables without a documented contract.

## Current-state warning

This is the target architecture. Existing modules remain during migration while imports, tests, Docker/Compose/Kubernetes manifests, scheduled jobs and CI are updated. A target directory or README is not proof of a runnable production service.
