# TELIXO Python Platform

Python owns data-plane computation and analytical processing only. Java owns the API/control plane and canonical transaction-domain APIs; Go owns event relay, quota enforcement and infrastructure monitoring; Elixir owns outbound webhook delivery and notification execution.

## Canonical Python services

| Service | Responsibility | Must not own |
|---|---|---|
| `transaction-ingestion` | Consume durably accepted provider events and approved imports; validate, normalize, deduplicate and publish versioned internal events | Public callback edge owned by Java where configured; tenant identity; canonical ledger; payment execution |
| `reconciliation-engine` | Match normalized provider transactions against the authorized ledger interface; classify discrepancies | A competing canonical ledger; payment movement, reversal or settlement |
| `data-quality` | Validate records, maintain quality findings, quarantine invalid data and expose quality metrics | Reconciliation decisions or provider authentication |
| `risk-scoring` | Produce explainable risk/anomaly signals from approved features and versioned rules/models | Final financial decisions, payment execution or duplicate risk engines |

Streaming, batch, analytics, feature engineering and model evaluation are **capabilities/libraries or jobs**, not additional always-on microservices by default. Split them only when independent scaling, ownership, SLOs or failure isolation justify it.

## Target layout

```text
Python/
  services/
    transaction-ingestion/
    reconciliation-engine/
    data-quality/
    risk-scoring/                 # existing service; migrate behind shared conventions
  shared/
    contracts/                    # Python adapters to root versioned contracts
    observability/                 # structured logging, metrics and tracing helpers
  jobs/
    batch/
    analytics/
    model-evaluation/
  tests/
    contract/
    integration/
    e2e/
  docs/
    ARCHITECTURE.md
    MIGRATION.md
```

The repository currently contains legacy modules under `app/`, `ingestion/`, `streaming/`, `ml/`, `data_quality/`, `analytics/` and `dags/`. These are compatibility sources during migration, not extra service ownership. Do not delete them until imports, Docker/Compose/Kubernetes/CI paths, scheduled jobs and tests have been migrated and verified.

## Integration and safety rules

- Python consumes provider events only after the configured edge has durably accepted them.
- Use versioned schemas and stable event IDs; idempotency must survive process restarts.
- Obtain tenant context from authenticated service metadata or a verified internal envelope, never an untrusted provider field alone.
- Use an outbox or equivalent recoverable publication; a publish attempt is not proof of delivery.
- Invalid events must be durably quarantined/DLQ'd with reason and correlation ID; never silently drop poison messages.
- Consumers must tolerate at-least-once delivery and support controlled replay.
- Reconciliation outcomes must be explainable and auditable.
- TELIXO does not initiate, confirm, refund, reverse, settle or move funds.
- Keep secrets in deployment secret managers; never commit credentials or production payloads.
- Every deployable service needs liveness/readiness, structured logs, metrics, tracing, graceful shutdown and bounded retries.

## Migration gates

1. Inventory imports, entry points, topics, tables and deployment references.
2. Add service contracts and isolated tests.
3. Move one capability at a time and update entry points and deployment manifests together.
4. Run unit, contract, integration and container smoke tests.
5. Compare outputs against legacy behavior using non-production data.
6. Verify staging recovery/replay and rollback.
7. Remove old modules only after repository-wide references and deployment configuration prove them unused.

See [service architecture](docs/ARCHITECTURE.md) and [migration plan](docs/MIGRATION.md). This refactor does not change production resources.
