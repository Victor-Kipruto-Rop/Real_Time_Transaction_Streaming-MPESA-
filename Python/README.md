# TELIXO Python Platform

Python owns transaction-data processing, reconciliation computation, quality validation, risk inference and analytical/ML data workflows. It must not duplicate Java's API/control plane or canonical transaction domain, Go's event relay/quota/infrastructure monitoring, or Elixir's outbound webhook and notification execution.

## The 10 planned services

| # | Service | Priority |
|---:|---|---|
| 1 | `transaction-ingestion` | Critical |
| 2 | `reconciliation-engine` | Critical |
| 3 | `data-quality` | Critical |
| 4 | `risk-scoring` | High |
| 5 | `stream-processing` | High |
| 6 | `batch-processing` | High |
| 7 | `analytics-metrics` | High |
| 8 | `feature-engineering` | High |
| 9 | `data-enrichment` | Medium |
| 10 | `model-evaluation-monitoring` | High |

These are ten explicit service boundaries and design specifications; they are not all implemented yet. Stream, batch, analytics and model-evaluation workloads may initially run as jobs/workers rather than continuously running services. Their ownership stays explicit; independent deployment should be justified by throughput, SLOs, fault isolation and operational cost.

## Target layout

```text
Python/
  services/
    transaction-ingestion/
    reconciliation-engine/
    data-quality/
    risk-scoring/
    stream-processing/
    batch-processing/
    analytics-metrics/
    feature-engineering/
    data-enrichment/
    model-evaluation-monitoring/
  shared/
    contracts/       # adapters to root contracts; no divergent schema copies
    observability/
    config/
  jobs/               # scheduled entry points, not competing service domains
  tests/
    unit/
    contract/
    integration/
    fault/
    e2e/
  docs/
    SERVICE_CATALOG.md
    ARCHITECTURE.md
    MIGRATION.md
```

## Non-negotiable boundaries

- Consume provider events only after durable acceptance at the configured Java edge.
- Canonical tenant, merchant and transaction-domain state remains Java-owned.
- Go owns event relay, quota enforcement and infrastructure monitoring; Elixir owns outbound webhook delivery and notification execution.
- TELIXO does not initiate, confirm, refund, reverse, settle or move funds.
- Use versioned contracts, stable event IDs, trusted tenant context, durable idempotency, outbox/inbox, DLQ/quarantine, replay and correlation IDs.
- Never fabricate enrichment or model results; represent unavailable/stale states explicitly.
- Keep secrets out of source control and minimize sensitive data in logs and event payloads.
- Do not delete legacy modules until imports, jobs, CI and deployment manifests are migrated and tests pass.

## Design gate before implementation

Review [service catalog](docs/SERVICE_CATALOG.md), [architecture](docs/ARCHITECTURE.md) and [migration plan](docs/MIGRATION.md). Each service needs approved API/event contracts, data ownership, threat model, SLO/runbook, failure/recovery plan and automated tests before implementation is considered ready.
