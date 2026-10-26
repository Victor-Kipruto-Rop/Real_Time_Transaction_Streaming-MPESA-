# TELIXO Python Platform Architecture

## Service boundaries and execution flow

The ten service responsibilities and per-service contracts are defined in [SERVICE_CATALOG.md](SERVICE_CATALOG.md) and the README under each `services/<service-name>/` directory.

1. **Java edge:** authenticate provider traffic and durably accept callbacks/requests. Python must not compete with this public edge.
2. **Transaction Ingestion:** consume accepted events, validate the trusted envelope, normalize and publish versioned internal events.
3. **Data Quality:** apply versioned schema/semantic rules. Invalid records receive durable reason-coded findings and quarantine references.
4. **Stream Processing:** run continuous event-time transformations with checkpoints and replay.
5. **Batch Processing:** run approved imports, historical backfills and bounded reprocessing jobs with checkpoints.
6. **Reconciliation Engine:** match valid normalized provider records against the authorized Java-owned ledger interface and emit explainable outcomes.
7. **Data Enrichment:** add only approved reference data, including source provenance and explicit unavailable states.
8. **Feature Engineering:** produce versioned, point-in-time-correct features from approved data.
9. **Risk Scoring:** compute explainable risk signals using approved feature/model versions.
10. **Analytics and Metrics:** publish tenant-scoped derived aggregates; Java APIs authorize dashboard access.
11. **Model Evaluation and Monitoring:** evaluate model quality and drift; recommendations do not silently promote models.

## Cross-platform ownership

- **Java:** identity, authorization, tenant/merchant control plane, configured public callback boundary and canonical transaction-domain APIs/state.
- **Python:** data processing, matching computation, quality findings, risk inference and analytics/ML workflows.
- **Go:** event relay, quota enforcement and infrastructure monitoring.
- **Elixir:** outbound webhook delivery, notification execution and delivery retry orchestration.
- **Frontend:** user experience only; it never talks directly to databases or internal brokers.

## Event and API contract rules

Every internal event should contain a stable `event_id`, `event_type`, `schema_version`, UTC occurrence/acceptance timestamps, `correlation_id`, trace context where available, source reference and tenant context from a verified internal envelope. Minimize personal/payment fields.

Consumers must tolerate at-least-once delivery. Commit broker offsets only after durable side effects; use an outbox for state-plus-publication atomicity. Poison events go to durable DLQ/quarantine with reason, attempt count and replay state. Replay must be controlled and audited. Use authenticated service-to-service calls, explicit timeouts, bounded concurrency, retry budgets and circuit breakers where appropriate.

## Data ownership

Java remains canonical owner of tenant, merchant and transaction-domain state. Python services own only declared processing metadata, derived results and execution state. Each service has one schema/migration owner. Shared writable tables require an explicit reviewed contract; analytics datasets are read-only relative to canonical state.

## Service implementation template

```text
services/<service-name>/
  README.md
  pyproject.toml
  Dockerfile
  src/telixo_<package>/
    __init__.py
    config.py
    logging.py
    health.py
    app.py                 # only if an HTTP/API entry point is needed
    domain/
    application/
    adapters/inbound/
    adapters/outbound/
    persistence/
  tests/
    unit/
    contract/
    integration/
    fault/
  deploy/                  # only deployment targets actually used
  docs/
    API.md
    EVENTS.md
    DATA_OWNERSHIP.md
    THREAT_MODEL.md
    RUNBOOK.md
```

Do not create boilerplate indiscriminately. Worker-only services need worker entry points, not artificial business APIs. Every deployable process needs appropriate health/readiness, structured logs, metrics, tracing, graceful shutdown, configuration validation and a service-specific CI path.

## Status

This is the agreed design target, not evidence that all ten runtime implementations exist. Existing legacy modules remain until dependency inventory, staged extraction, test verification and deployment updates are complete.
