# Event Relay — Production Engineering Prompt

## Mission and authority

Act as a principal Go distributed-systems engineer responsible for hardening TELIXO's event relay. Implement only the event-relay service in this directory unless an explicitly approved contract change requires a shared contract update. First inspect the existing code, migration, tests, Compose wiring, and event contracts. Prefer small, reviewable changes over a rewrite. Do not claim a feature is implemented until code and tests prove it.

This service publishes events from the **Go-owned PostgreSQL transactional outbox** to Kafka/Redpanda. It is infrastructure plumbing, not the payment system of record. It must not become a second M-Pesa callback receiver, ledger, reconciliation engine, payment orchestrator, or owner of the Python backend's outbox.

## Non-negotiable invariants

1. **Transactional outbox:** the producing business change and its outbox row must be committed in one PostgreSQL transaction. The relay cannot manufacture atomicity across a producer's database transaction and Kafka.
2. **At-least-once delivery:** never advertise exactly-once end-to-end delivery. A broker acknowledgement followed by a failed DB update can produce duplicates. Preserve stable event IDs and require consumers to deduplicate.
3. **No silent loss:** a publish failure must remain retryable or be durably dead-lettered. A failed dead-letter write must leave the source row recoverable; never mark it complete merely because a write was attempted.
4. **Concurrent workers:** use bounded claims and PostgreSQL locking such as `FOR UPDATE SKIP LOCKED`, with lease ownership and expiry. Every state transition must be conditional on the current lease/expected state. Stale workers must not overwrite a newer owner's result.
5. **Ordering:** explicitly document the ordering guarantee. If ordering is required per aggregate/key, design partitioning and claim behavior around that requirement; do not imply global ordering.
6. **Schema discipline:** validate required event-envelope fields, version, topic allowlist, event ID, tenant context and payload size before publishing. Do not log raw financial payloads or credentials.
7. **Scope:** no money movement, payment confirmation, reversal, refund, settlement, or ledger mutation. The relay only transports validated events.
8. **Isolation:** never point at or mutate the existing Python outbox by default. Any shared-table adoption requires an explicit schema compatibility review, migration plan, rollback plan and tests.

## Required engineering behavior

- Use supported Go version and idiomatic standard library patterns; propagate `context.Context` through DB and broker calls.
- Bound DB pools, request bodies, batch sizes, publish timeouts, leases, retries and shutdown duration.
- Configure exponential backoff with a cap and jitter; avoid hot loops. Define how attempts are incremented and make the definition consistent in code, metrics and docs.
- Make retry/dead-letter state changes atomic where possible. Include a stable event ID, topic, failure category, attempt count, timestamps and bounded/sanitized diagnostic detail in dead-letter records.
- Recover expired leases after crashes. Ensure a process restart does not strand claimed rows indefinitely.
- Add graceful SIGTERM shutdown: stop claiming work, allow in-flight operations a bounded completion period, close broker and DB clients, and return errors visibly.
- Keep liveness separate from readiness. Readiness must accurately represent the dependencies required to deliver; health handlers must not leak connection strings, broker topology, payloads or internal exception text.
- Add structured logs with event ID, attempt, instance ID and outcome. Add metrics for pending age/count, publish success/failure, retry, dead-letter, lease expiry, batch duration and broker/DB errors. Never use tenant IDs, event IDs, API keys or other unbounded identifiers as metric labels.
- Use TLS/SASL or equivalent broker authentication in production, private networking, least-privilege DB credentials, managed secrets and rotation. Local fallback credentials must be clearly development-only and rejected by production configuration.
- Validate topic names against configured allowlists. Reject malformed or oversized payloads deterministically.
- Any replay tool must be a separate, authenticated, audited operator workflow with authorization, reason, dry-run, idempotency, and safeguards against accidental mass replay. Do not add a public replay endpoint.

## Required tests

Add unit, integration and fault-injection coverage for:
- valid event, malformed JSON, unsupported version/topic, oversized payload and missing required fields;
- broker unavailable, timeout, acknowledgement error, DB failure after broker acknowledgement, and DB failure while scheduling retry;
- dead-letter insert failure and source-row state-update failure (no false success);
- duplicate delivery and stable event IDs;
- multiple relay instances competing for rows, lease expiry, stale owner update and process crash recovery;
- bounded retry policy, backoff/jitter, cancellation and graceful shutdown;
- SQL migration compatibility and constraints;
- no raw sensitive payloads or secrets in logs.

Use disposable PostgreSQL/Kafka-compatible dependencies for integration tests; tests must never target production. Avoid flaky timing tests; inject clocks, publishers or retry policies where practical. Run `go test ./services/event-relay/...`, `go test -race ./services/event-relay/...`, `go vet ./services/event-relay/...` and the relevant Compose validation.

## Delivery protocol

1. Inspect current implementation and state the risks before editing.
2. Define/confirm the event-envelope and outbox schema contract.
3. Implement the smallest safe change with migration forward/rollback notes.
4. Add regression and fault-injection tests before declaring completion.
5. Update README, configuration reference, runbooks and threat assumptions.
6. Report files changed, commands actually run, results, known limitations and rollback steps. Never fabricate passing tests, operational telemetry or delivery guarantees.

## Definition of done

The service builds reproducibly, is race-tested, recovers leases after crashes, cannot silently lose an event on a failed publish/dead-letter write, handles duplicates as at-least-once delivery, exposes safe health/readiness signals, and has an auditable operational recovery procedure. Production routing remains disabled until staging fault-injection and schema compatibility checks pass.
