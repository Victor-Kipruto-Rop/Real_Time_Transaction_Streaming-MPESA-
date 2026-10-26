# Python Service Migration Plan

## Phase 0 — Inventory and baseline
- Inventory imports and entry points across `Python/`, root Compose files, Dockerfiles, Kubernetes, Terraform, CI, DAGs, scripts and tests.
- Record current unit/integration test results and build status.
- Assign one owner to each table and topic.
- Check for credentials and production payloads in tracked files.

## Phase 1 — Contracts and shared primitives
- Agree versioned event schemas with Java and Go; coordinate with root `contracts/` rather than creating divergent copies.
- Define trusted tenant envelope, event ID, schema version, correlation ID and timestamp rules.
- Establish shared observability/configuration helpers without coupling domain logic between services.
- Add contract tests and schema compatibility checks.

## Phase 2 — Transaction ingestion
- Move the durable consumer/normalization pipeline first.
- Keep the current Python receiver if it still serves traffic; migrate callback traffic to the configured Java boundary and verify before disabling it.
- Ensure durable receipt/outbox, idempotency, DLQ and replay before switching consumers.
- Update Docker, Compose, Kubernetes, scheduled jobs and monitoring in the same change.

## Phase 3 — Data quality and reconciliation
- Extract validators and quarantine logic into data-quality.
- Extract matching logic into reconciliation-engine; test exact, partial, duplicate, missing and conflicting records, decimal precision, timezones and late arrivals.
- Access canonical ledger state through the documented owner API or approved read model.
- Require explainable match reasons and deterministic replay.

## Phase 4 — Risk scoring
- Keep risk-scoring as the sole Python risk inference boundary.
- Version models/features/rules, record reason codes, monitor drift and evaluate false positives/negatives.
- Remove duplicate implementations only after all consumers are verified.

## Phase 5 — Remove compatibility modules
Delete old modules only after repository-wide references and dynamic imports are checked; tests pass; Docker/Compose/Kubernetes/CI and deployment commands are updated; DAGs/scripts are updated; staging smoke, replay and rollback tests pass; and data/migration ownership is documented.

## Rollback
Keep legacy entry points available until staging comparison and recovery pass. Avoid dual-writes to canonical state. If comparison runs in parallel, make it read-only and label its metrics. Revert routing/configuration before schema changes.
