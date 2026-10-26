# Python Service Catalog and Design Baseline

TELIXO Python has exactly ten planned service boundaries. This catalog defines ownership before implementation. It does not assert that each service is already implemented or deployable.

| # | Service | Type | Primary responsibility | Main dependency |
|---:|---|---|---|---|
| 1 | `transaction-ingestion` | Core service | Consume provider events only after the configured Java boundary has durably accepted them, and normalize approved imports into canonical internal event envelopes. | Kafka/Redpanda |
| 2 | `reconciliation-engine` | Core service | Deterministically match normalized provider records to authorized canonical ledger records and classify discrepancies with explainable evidence. | Java ledger API/read model |
| 3 | `data-quality` | Core service | Apply versioned schema, semantic and cross-record rules, record quality findings, and quarantine invalid records for controlled recovery. | Root schemas/contracts |
| 4 | `risk-scoring` | Core service | Generate explainable risk/anomaly signals from approved transaction features using versioned rules and models. | Feature Engineering |
| 5 | `stream-processing` | Processing/analytics service | Run scalable continuous transformations and event-time aggregations over durable internal topics; coordinate stream checkpoints and replay. | Kafka/Redpanda |
| 6 | `batch-processing` | Processing/analytics service | Execute scheduled imports, historical backfills, reconciliation reruns and bounded data repair jobs with resumable checkpoints. | Scheduler/orchestrator (existing platform) |
| 7 | `analytics-metrics` | Processing/analytics service | Produce tenant-scoped operational and business aggregates about ingestion, reconciliation, data quality and risk outcomes. | Read-only analytical data source |
| 8 | `feature-engineering` | Processing/analytics service | Build validated, versioned features for risk scoring and model evaluation from approved transaction and aggregate data. | Curated analytical source |
| 9 | `data-enrichment` | Processing/analytics service | Enrich approved records with authorized reference data such as merchant metadata, classification mappings and configured business reference lists. | Java-owned merchant/tenant APIs |
| 10 | `model-evaluation-monitoring` | Processing/analytics service | Evaluate model versions and monitor drift, calibration, latency, missing features and outcome quality without controlling transaction processing. | Risk-scoring metadata/events |

## Global rules

- Java owns identity, tenant/merchant control plane, canonical transaction-domain APIs and the configured public callback edge.
- Python consumes durably accepted events; it must not create a competing callback receiver or canonical ledger.
- Go owns event relay, quota enforcement and infrastructure monitoring.
- Elixir owns outbound webhook delivery and notification execution.
- No Python service may initiate, confirm, refund, reverse, settle or move funds.
- Every event-driven service requires stable IDs, versioned schemas, tenant context from a trusted internal envelope, idempotency, bounded retries, durable DLQ/quarantine, replay and correlation IDs.
- Every service has a single declared data owner, schema/migration owner, SLO, runbook and service-specific tests.
- Shared libraries may contain contracts/telemetry/config helpers, but never merge distinct service domains into one implicit mega-service.
- Services 5–10 must not become separate always-on processes until their operational need and scaling boundary are validated; their service boundary and deployable design are still specified now.
- No legacy modules are deleted until references, jobs, imports, CI and deployment manifests have been migrated and tested.

## Design-before-build gate

Each service needs: context diagram, API/event contract, schema ownership, threat model, tenant-isolation plan, idempotency/retry/DLQ/replay design, dependency and timeout policy, observability/SLO, migration/rollback plan, unit/contract/integration/fault tests, container build and CI checks. Build implementation only after this design is reviewed and cross-language contracts agree.

## Dependency order

1. Contracts, identity propagation and telemetry conventions.
2. Data Quality and Transaction Ingestion foundations.
3. Stream Processing and Batch Processing execution patterns.
4. Reconciliation Engine and its Java-owned ledger interface.
5. Feature Engineering and Data Enrichment.
6. Risk Scoring using versioned features.
7. Analytics and Metrics plus Model Evaluation and Monitoring.
8. Cross-service fault-injection, security, replay and performance acceptance.
