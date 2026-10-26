# Python Service Design Review Checklist

Use this checklist for each of the ten services before implementation begins. Mark an item complete only when there is a reviewed artifact or automated test to prove it.

## Product and ownership
- [ ] One-sentence purpose and explicit non-goals approved.
- [ ] Service owner and on-call/operational owner named.
- [ ] Input/output contracts versioned and agreed with Java, Go, Elixir and frontend/API consumers where applicable.
- [ ] Every topic, table, schema, object-storage prefix and model artifact has one declared owner.
- [ ] Synchronous API versus asynchronous event choice justified.

## Security and tenant isolation
- [ ] Threat model and trust boundaries documented.
- [ ] Tenant context originates from authenticated metadata or verified internal envelope.
- [ ] Authorization enforced at each service boundary; cross-tenant negative tests exist.
- [ ] Secrets stored outside source control; rotation procedure documented.
- [ ] Sensitive data minimized, masked in logs, encrypted and retained according to policy.
- [ ] SSRF, unsafe deserialization, injection, resource exhaustion and dependency risks reviewed where relevant.

## Reliability and data correctness
- [ ] Idempotency key and deduplication retention defined.
- [ ] Outbox/inbox or equivalent recovery pattern documented where state and event publication interact.
- [ ] Retryable vs permanent errors classified; retries bounded with jitter and timeouts.
- [ ] Durable DLQ/quarantine, reason codes, replay authorization and audit history defined.
- [ ] Ordering, late data, duplicates, poison messages and schema evolution policies defined.
- [ ] Graceful shutdown, checkpoint/restart and backpressure behavior tested where applicable.
- [ ] No service initiates, confirms, refunds, reverses, settles or moves funds.

## Operations
- [ ] SLOs, latency/throughput targets and capacity assumptions documented.
- [ ] Health/readiness semantics, metrics, traces, structured logs and correlation IDs defined.
- [ ] Alerts, dashboard and runbook prepared.
- [ ] Dependency timeout/circuit-breaker policy and degraded mode documented.
- [ ] Docker build, pinned dependency policy, configuration validation and CI are reproducible.
- [ ] Rollback and schema migration strategy tested.

## Test evidence
- [ ] Unit and property-based tests for core rules.
- [ ] Contract and compatibility tests.
- [ ] Integration tests using controlled dependencies.
- [ ] Fault-injection tests for database/broker/dependency outage and process crash.
- [ ] Load and resource-bound tests.
- [ ] Security and tenant-isolation tests.
- [ ] Staging replay and rollback evidence captured.

## Approval
Do not implement or call the service production-ready until its contract, data ownership, threat model, failure/recovery design, SLO/runbook and test plan are reviewed. Do not delete legacy implementations until the replacement is verified in staging.
