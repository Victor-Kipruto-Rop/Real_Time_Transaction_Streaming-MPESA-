# Python Ten-Service Design and Migration Plan

## Stage 1 — Design and contract agreement
- Review the ten service boundaries in `SERVICE_CATALOG.md` and each service README.
- Agree API/event schemas and tenant-context propagation with Java, Go and Elixir.
- Map every legacy file, import, topic, table, DAG, script, container and CI path to one owner.
- Decide which workloads run continuously versus as scheduled jobs based on load, SLOs, fault isolation and operating cost.
- Review threat models, retention, data minimization, SLOs, runbooks and failure handling.

## Stage 2 — Platform foundations
- Establish versioned contract tests, verified tenant context, correlation IDs, telemetry conventions and dependency timeouts.
- Create a reproducible local integration environment.
- Assign one schema/migration owner per service and document secrets management.

## Stage 3 — Migrate incrementally
1. Transaction Ingestion and Data Quality.
2. Stream Processing and Batch Processing.
3. Reconciliation Engine against the Java-owned ledger interface.
4. Data Enrichment and Feature Engineering.
5. Risk Scoring with versioned features and models.
6. Analytics and Metrics.
7. Model Evaluation and Monitoring.

For each service: move implementation code, update imports/package metadata, tests, Docker/Compose/Kubernetes and CI together; run unit, contract, integration and fault tests; compare outputs with legacy behavior on non-production data; validate replay/rollback in staging; then mark migrated.

## Stage 4 — Remove legacy code
Delete a legacy module only after static and dynamic references, scripts, DAGs, tests, deployment manifests and CI prove it unused. Verify asset retention before removing backups. Never bulk-delete based on filenames alone.

## Release gates
- Negative tests prove tenant isolation.
- Idempotency survives restarts and controlled replay.
- No event is acknowledged before durable side effects commit.
- Poison-message DLQ and audited replay are demonstrated.
- Timeouts, retry budgets, bounded concurrency, backpressure and graceful shutdown are tested.
- Dashboards, alerts, runbooks and rollback are ready.
- No production deployment is part of this design phase.
