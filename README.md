# PesaGuard Transaction Streaming

Python-based M-Pesa transaction ingestion and event-streaming subsystem for the PesaGuard fintech platform.

This repository is responsible for accepting provider callbacks, validating and normalizing provider events, publishing durable events, tracking ingestion/processing delivery state, and supplying operational analytics. It is **not** the owner of PesaGuard tenant identity, the canonical transaction ledger, reconciliation decisions, payment execution, or settlement.

## Integration status

This repository is being aligned with the PesaGuard backend and its Java services through a staged, backwards-compatible migration.

- Existing runtime paths and deployment manifests are retained while compatibility is audited.
- Shared event contracts are maintained in `contracts/events/`.
- Integration boundaries and migration rules are documented in `docs/PESAGUARD_INTEGRATION.md`.
- The source tree is not considered fully migrated to the `src/` package until imports, Docker images, CI, scheduled jobs and deployment manifests have been updated and tested.
- No production traffic or infrastructure is changed by repository refactoring alone.

## Responsibilities

### This repository owns
- Callback receipt and provider-specific payload validation.
- Provider payload normalization into versioned internal events.
- Durable ingestion receipts, processing attempts and delivery state.
- Outbox/retry/dead-letter mechanisms for its own event delivery.
- Streaming worker health, metrics and operational recovery.
- Streaming-focused analytical transformations where access is approved.

### PesaGuard core services own
- Tenant identity, membership, roles and authorization.
- Canonical financial transaction records and their lifecycle.
- Merchant onboarding and Daraja credential ownership.
- Reconciliation decisions and reconciliation state.
- Developer API keys, public API access and customer-facing authorization.
- Any payment execution, reversal or settlement capability (which must remain separate from callback ingestion).

## Repository map

| Area | Purpose |
|---|---|
| `app/`, `ingestion/`, `streaming/`, `kafka.py` | Existing runtime modules retained during compatibility migration |
| `schemas/`, `contracts/events/` | Payload validation and cross-language event contracts |
| `dbt/`, `analytics/`, `data_quality/`, `ml/` | Analytics, data quality and risk research; not canonical transaction writes |
| `grafana/`, `dashboards/`, `monitoring/` | Dashboards, metrics and alerting configuration |
| `docker-compose*.yml`, `Dockerfile*`, `kubernetes/`, `terraform/`, `deploy/` | Existing deployment assets; review before changing service paths |
| `tests/` | Unit, integration, end-to-end, load and benchmark tests |
| `docs/` | Architecture, operations, security and integration guidance |
| `src/pesaguard_streaming/` | Destination package for the staged runtime migration; existing entry points remain authoritative until migration gates pass |

## Local development

Use the existing repository-specific setup and configuration documented in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) and [CONTRIBUTING.md](CONTRIBUTING.md). Do not use production credentials for local development.

Run the current baseline tests with the repository's existing environment:

```bash
python -m pytest tests/unit tests/integration tests/e2e -q
```

Some integration tests require PostgreSQL, Kafka/Redpanda or provider test configuration. Run the tests relevant to the services available in your environment and record skipped tests explicitly.

## Event-driven integration

The intended flow is:

```text
Daraja callback
    -> ingestion validation and durable receipt
    -> recoverable event publication (outbox or proven equivalent)
    -> versioned Kafka/Redpanda event
    -> canonical PesaGuard transaction owner
    -> Java reconciliation / risk workflows
    -> persisted results exposed through authorized PesaGuard APIs
```

The streaming service must not treat a broker publish attempt as proof of delivery. Consumers must be idempotent, malformed messages must be recoverable, and tenant context must come from trusted server-side configuration—not an untrusted callback field.

See [PesaGuard integration boundaries](docs/PESAGUARD_INTEGRATION.md) and [event contracts](contracts/events/README.md).

## Production safety

- Never commit real credentials, access tokens, customer data or production payloads.
- Do not trust callback payloads as proof of tenant identity or payment authenticity.
- Do not create a second authoritative transaction ledger.
- Do not publish an event before its durable acceptance/recovery guarantees are established.
- Do not mark an event delivered solely because a publish call returned without an exception.
- Do not silently skip poison messages or advance offsets without a documented recovery policy.
- Do not deploy a structural refactor to production until CI, migration compatibility, staging smoke tests and rollback have passed.

## Documentation

- [PesaGuard integration boundaries](docs/PESAGUARD_INTEGRATION.md)
- [Repository reorganization plan](docs/REPOSITORY_REORGANIZATION.md)
- [Event contract guidance](contracts/events/README.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Production runbook](docs/PRODUCTION_RUNBOOK.md)
- [Rollback checklist](docs/ROLLBACK_CHECKLIST.md)
- [Security policy](SECURITY.md)
