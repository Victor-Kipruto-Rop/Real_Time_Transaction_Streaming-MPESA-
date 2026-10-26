# Stream Processing Service

**Purpose:** Continuous event-time transformations and windowed aggregates over durable internal topics.

## Contract
- **Inputs:** Versioned internal events emitted by ingestion and data-quality services.
- **Outputs:** Derived versioned events, window aggregates and checkpoint metadata.
- **Owns:** Job-specific checkpoint and derived state only.
- **Must not own:** Primary ingestion receipts, reconciliation decisions, event relay, outbound webhooks.
- **Dependencies:** Kafka/Redpanda, approved stream runtime, root contracts/schema registry, state store, telemetry.

## Reliability and security
Checkpointed restart, backpressure, bounded state, explicit late-event policy, durable poison-message routing and controlled replay.

Every event-driven handler must validate the trusted tenant envelope and schema version, use stable event IDs and durable idempotency, attach correlation/trace context, minimize sensitive fields, and support a durable dead-letter/quarantine path with controlled replay. Authenticate service calls with workload identity or short-lived credentials; use explicit timeouts, bounded concurrency and retry budgets. Keep secrets out of source control.

## Acceptance tests
Partition rebalance, duplicate/out-of-order events, checkpoint restore, backpressure, schema evolution, replay correctness and tenant isolation.

## Build readiness
This is the approved design boundary, not an implemented service. Before implementation, agree the API/event schemas with other platform owners, document schema/migration ownership and SLOs, add threat model and runbook, then build the package, tests, container and CI workflow together.
