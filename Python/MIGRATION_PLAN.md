# Python backend migration plan

## Scope and baseline

Source: `Victor-Kipruto-Rop/api.pesaguard/pesaguard_backend_pipeline`, branch `main`, inspected at source commit `4a9037f7ee805f1a6e7413f5728eb2f7f056f984`.

The source tree contains 459 files under `pesaguard_backend_pipeline/`, including 148 test files and 59 Alembic-related files/entries. It has a FastAPI control plane mounting a Flask dashboard/API, PostgreSQL/SQLAlchemy, Redis/RQ, Kafka-compatible streaming, Daraja validation, transaction ingestion/idempotency, reconciliation, risk scoring, communications, IAM/API-key logic, observability, operations scripts and deployment support.

This migration is incremental. Do not delete or rewrite the source backend until parity tests and data/schema ownership are proven. TELIXO's existing Java, Go and Elixir services are the intended owners for overlapping platform capabilities.

## Service ownership proposal

| Python service / package | Source modules to reuse | Decision | Boundary |
|---|---|---|---|
| Risk scoring | `fraud_risk_engine.py`, selected anomaly/rule modules and tests | **Extracted first** | Stateless, explainable scoring; no payment execution or persistence in the first cut |
| Transaction ingestion | `ingestion.py`, `validators.py`, `schema_validation.py`, `normalization.py`, `connectors/mpesa/`, `shared/daraja/` | Keep and refactor | Consume validated provider events; Java owns public callback intake once its implementation is verified |
| Reconciliation | `reconciliation_engine.py`, `reconciliation_job.py`, `reconciliation_scoring.py`, `reconciliation_utils.py`, discrepancy/match code | Keep and extract after ingestion | Match provider transaction records to tenant ledger imports; persist explainable match/discrepancy outcomes |
| Data quality and lineage | `data_quality.py`, `dq_rules.py`, `data_profiling.py`, `data_catalog.py`, `data_dictionary.py`, `lineage.py`, `provenance.py`, `transformation_store.py` | Keep; consolidate | Data validation, lineage, quality metrics and analytics; avoid a second transaction system of record |
| Analytics / reporting | `aggregation_service.py`, `scheduled_reports.py`, `export_routes.py`, report/query modules | Keep only business-critical features | Python produces analytical aggregates; frontend owns presentation |
| Python worker adapters | `event_consumer.py`, `realtime_worker.py`, selected Kafka modules | Keep selectively | Consume versioned internal events with idempotent handlers and bounded retries |
| IAM / tenant / API keys | `auth_rbac.py`, `authorization_policy.py`, `models.py` IAM/API-key entities and related tests | **Temporary compatibility only** | Do not remove until Java auth, tenant scoping, key lifecycle and audit behavior are tested end-to-end |
| Communications | `communications/`, `alerting_service.py`, `notifier.py`, provider adapters | Migrate ownership to Elixir where equivalent delivery exists | Avoid two webhook/email/SMS retry systems; retain Python only for domain events or adapters with no Elixir equivalent |
| Database schema and migrations | `models.py`, `alembic/`, `migrations/`, SQL scripts | Preserve as source of truth during transition | No split database or migration deletion until table ownership, backfill, rollback and compatibility are designed |
| Operations / observability | health, metrics, tracing, backup/restore, smoke tests | Keep cross-cutting standards; place deployment config in `Infrastructure/` | Python services expose standard health/metrics/traces; platform deployment remains under `Infrastructure/` |

## Keep / refactor / defer / remove candidates

### Keep

- Idempotency and uniqueness constraints for provider events.
- Transactional outbox and durable dead-letter/replay behavior.
- Daraja payload validation and canonical transaction normalization.
- Reconciliation matching, ambiguity handling, quality/release gates and ground-truth tests.
- Tenant-scoped data access, audit trail and append-only financial history.
- Alembic history, database integrity tests, security tests and production-readiness checks.
- Health/readiness, structured logs, trace/correlation IDs and backup/restore drills.

### Refactor

- `app.py`, `fastapi_app.py`, `canonical_app.py` and `api/dashboard_app.py`: map every route first, then retain one service entrypoint per owned API. The dashboard API is large and should not be mechanically deleted.
- `app_1.py`, `app_2.py`, `app_3_features.py` and other versioned app variants: identify active imports/deployment references; archive or remove only when proven unused.
- Large `models.py`: split model modules by domain only after migration ownership is documented; do not change table names/constraints casually.
- Multiple event buses, queues and worker entrypoints: define one durable event contract and one owner for each event type.

### Defer or move to another platform

- API gateway, developer portal, tenant/auth management, API-key issuance and quota enforcement: Java/Go ownership where existing TELIXO services already cover the capability.
- High-concurrency webhook delivery, email/SMS provider retries and delivery state machine: Elixir ownership once parity and delivery guarantees are verified.
- Generic dashboards/UI assets: frontend ownership; retain backend query endpoints only until the frontend is migrated.
- Airtel/bank/POS connectors: keep behind adapter interfaces and mark development-only unless live integration tests and provider credentials prove readiness.
- AI assistant, campaign, localization, optional search, and experimental algorithm modules: keep only if an explicit product requirement, consumer, and tests justify them.

### Remove only after evidence

- Duplicate Flask/FastAPI routes or duplicate app variants after route parity and deployment reference checks.
- RQ jobs that are fully replaced by durable Kafka consumers or scheduled jobs with equivalent retry, idempotency, and observability.
- Python communications delivery paths after Elixir handles all required providers and retries.
- Stale demo/sample/experimental modules with no imports, route registrations, migrations, test coverage, or product owner.
- Unused dependencies only after an import/deployment audit and clean isolated builds.

**No source component is deleted in this change.** Removal is an explicit later migration with tests and a rollback plan.

## Financial and multi-tenant invariants

1. Callback receipt is not proof that funds moved; this system reconciles events and does not initiate, confirm, reverse, refund, or settle payments.
2. Tenant identity must come from authenticated internal context or a verified provider-account mapping, never from an untrusted body field alone.
3. Every financial query, idempotency key, replay, risk assessment and reconciliation match must be tenant-scoped.
4. Event publication uses a transactional outbox or equivalent durable handoff; a failed publish must not be recorded as delivered.
5. Malformed events are durably dead-lettered with reason and correlation metadata before offsets advance.
6. Consumers are idempotent. Delivery is described as at-least-once unless stronger end-to-end guarantees are proven.
7. Keep the current schema/migrations intact until service ownership, data migration, dual-read/write strategy and rollback are tested.
8. No production deploy, secret rotation, or production database mutation is part of this migration.

## Execution phases

- [x] Inspect source tree and identify core modules, tests, migrations and deployment structure.
- [x] Create first extracted Python risk-scoring service using the existing risk engine.
- [ ] Run risk-scoring unit/API tests and container build in CI.
- [ ] Map and extract transaction ingestion without creating a second public Daraja callback endpoint.
- [ ] Extract reconciliation with golden datasets and exact/partial/ambiguous/unmatched cases.
- [ ] Assign event contracts and table ownership with Java/Elixir/Go.
- [ ] Migrate remaining tests and migration history needed by retained modules.
- [ ] Remove proven duplicate/unused components in separate, reviewable commits.
- [ ] Run integration, tenant-isolation, replay, outbox/dead-letter, migration and staging smoke tests before merging.

## Validation status

The initial service scaffold and workflow have been committed to the migration branch. This document does not claim that CI has passed or that the new service is production-ready. Risk-scoring behavior must be tested against the source golden cases and integrated with tenant-scoped event consumption before production use.
