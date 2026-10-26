# Python Service Catalog and Design Baseline

TELIXO Python has exactly ten planned service boundaries. This catalog defines ownership before implementation. It does not assert that each service is already implemented or deployable.

| # | Service | Priority | Type | Primary responsibility | Main dependency |
|---:|---|---|---|---|---|
| 1 | `transaction-ingestion` | Critical | Core | Consume durably accepted events/imports, normalize provider records and deduplicate processing. | Kafka/Redpanda |
| 2 | `reconciliation-engine` | Critical | Core | Match normalized provider records to the authorized ledger interface and classify discrepancies with explainable evidence. | Java ledger API/read model |
| 3 | `data-quality` | Critical | Core | Validate schemas, required fields, timestamps, amounts, currency and record consistency; quarantine invalid records. | Root schemas/contracts |
| 4 | `risk-scoring` | High | Core | Generate explainable risk scores/anomaly signals using approved, versioned features, rules and models. | Feature Engineering |
| 5 | `stream-processing` | High | Processing | Process transaction events and analytical signals with checkpointing and replay. | Kafka/Redpanda |
| 6 | `batch-processing` | High | Processing | Run scheduled imports, historical reconciliation, backfills and large-volume jobs. | Scheduler/orchestrator |
| 7 | `analytics-metrics` | High | Analytics | Calculate reconciliation rates, transaction trends, discrepancy summaries and operational/business indicators. | Read-only analytical source |
| 8 | `feature-engineering` | High | ML data | Prepare validated, versioned, point-in-time-correct features for risk models and anomaly detection. | Curated analytical source |
| 9 | `data-enrichment` | Medium | Data preparation | Normalize/enrich using approved reference data and provenance; never invent missing transaction facts. | Java-owned merchant APIs |
| 10 | `model-evaluation-monitoring` | High | ML evaluation | Evaluate model quality, detect drift, track false positives/negatives and support controlled model-version changes. | Risk-scoring metadata/events |

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
