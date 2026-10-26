# Repository Reorganization Plan

## Strategy

Use an incremental migration rather than a single large move. The repository contains multiple runtime entry points and deployment systems; moving files without updating imports and deployment manifests would create a broken release.

The first integration change establishes service boundaries, contract governance and a target package. Existing runtime paths remain in place until the compatibility gate for each component passes.

## Target logical layout

```text
contracts/
  events/                 # Versioned Python/Java event schemas
  openapi/                # Internal HTTP contract specifications
src/pesaguard_streaming/
  config/                 # Environment-backed configuration
  ingestion/              # Provider callback endpoints and validation
  providers/mpesa/        # Daraja-specific client, payloads and normalization
  messaging/              # Producers, consumers, outbox, retries and DLQ
  processing/             # Idempotent streaming processing
  tenancy/                # Trusted tenant-context resolution interfaces
  integrations/           # Authenticated PesaGuard internal clients
  observability/          # Health, metrics, tracing
analytics/                # Python analytical jobs
dbt/                      # SQL transformations and dbt tests
infrastructure/
  kafka/                  # Topic/ACL/schema-registry definitions
  postgres/               # Operational database migration assets
observability/
  prometheus/
  grafana/
tests/
  unit/
  integration/
  contract/
  security/
  failure_recovery/
  e2e/
docs/
  architecture and operational runbooks
```

This is a target layout, not a claim that all modules have already moved or that each folder should become a separate microservice. A separate deployment process is justified only where independent scaling, isolation or operational ownership requires it.

## Existing directories and intended destination

| Existing path | Intended treatment |
|---|---|
| `app/` | Migrate in stages to `src/pesaguard_streaming/`; keep old imports/entry points compatible until consumers are updated |
| `ingestion/` | Split provider-specific behavior, messaging and persistence into package modules; avoid copying implementations |
| `streaming/`, `kafka.py` | Consolidate overlapping producer/consumer code only after call sites and tests identify the active implementation |
| `schemas/` | Keep provider/API validation models separate from versioned cross-service event contracts |
| `dbt/`, `analytics/`, `data_quality/`, `ml/` | Keep analytics read-only with respect to canonical financial records; document source tables and data ownership |
| `grafana/`, `dashboards/`, `monitoring/` | Consolidate observability configuration after checking provisioning paths and dashboard references |
| `dags/` | Preserve orchestrator-discovered paths and dependencies; do not move DAGs without updating scheduler configuration |
| `Dockerfile*`, Compose files | Update working directories, copy paths, module entry points and health checks only with the associated code move |
| `kubernetes/`, `terraform/`, `deploy/` | Preserve deployment assets until the new runtime layout has passed staging validation |
| `backups/` | Treat as historical recovery material, not active source code; inspect for sensitive data and keep out of runtime images |

## Required migration gates

### Gate A — Inventory and baseline
- Record active entry points and imports.
- Identify which Kafka producer and consumer implementations are used.
- Map Docker, Compose, Kubernetes, Terraform, Airflow and GitHub workflow references.
- Run the existing test suite and record environment-dependent skips.
- Inspect the secret scan and ensure no credentials are added to commits.

### Gate B — Contracts
- Identify the canonical transaction and reconciliation owners in the PesaGuard backend.
- Agree event schema, tenant-context provenance, idempotency keys, money representation and timestamp semantics.
- Add Python/Java contract compatibility tests.
- Confirm no consumer relies on undocumented fields.

### Gate C — Package migration
- Move one cohesive module group at a time.
- Add temporary compatibility imports where necessary.
- Update all entry points, Dockerfiles, Compose, DAGs, health checks and deployment manifests.
- Remove old paths only after reference search and tests show no remaining use.

### Gate D — Durability and tenancy
- Test outbox recovery after database commit/broker outage.
- Test duplicate callbacks and concurrent deliveries.
- Test consumer crash before and after database commit.
- Test malformed event handling, DLQ replay and offset behavior.
- Test cross-tenant access attempts and unresolved tenant context.

### Gate E — Staging release
- Build all runtime images.
- Run unit, integration, contract, security and smoke tests.
- Confirm dashboards and alerts use the new service names and metrics.
- Test rollback to the prior image/configuration.
- Do not route production callbacks to the new path until explicitly approved.

## Definition of done

The reorganization is complete only when:
1. The package layout is canonical and old paths are removed or documented as intentional compatibility shims.
2. All runtime and orchestration references point to valid files and import paths.
3. CI builds the service images and tests the contracts.
4. The durable processing and failure-recovery tests pass.
5. Tenant isolation and secret-handling checks pass.
6. Staging smoke tests and rollback are demonstrated.
7. Documentation describes implemented behavior rather than aspirational behavior.

This plan does not itself prove these gates have passed.
