# Integration Health Service — Operations and recovery

## Implemented baseline
- Authenticated tenant-scoped API boundary; tenant identity is derived from verified bearer claims, not trusted from the request body.
- PostgreSQL record persistence with idempotency uniqueness and guarded state transitions.
- Transactional outbox writes, leased event claims, bounded retry scheduling, dead-letter status, and an HTTPS relay.
- Service-specific deterministic request validation documented in the service Domain.Processor module.

## Service-specific production work still required
Implement provider-specific authenticated probes, safe credential checks, latency budgets, circuit-breaker state, callback delivery checks, alert thresholds, and metrics. Current code validates check requests but does not execute provider probes.

## Reliability and security controls
- Require TLS for external traffic and event-relay calls. Never log bearer tokens, signing secrets, raw credentials, or sensitive payloads.
- Treat relay delivery as at-least-once; downstream consumers must deduplicate by event ID/Idempotency-Key.
- Alert on database readiness failures, growing outbox backlog, retry exhaustion, expired leases, and dead-letter growth.
- Replay only through an authenticated operator workflow with authorization, reason capture, and audit records.
- Before release, test cross-tenant reads/writes, concurrent idempotency keys, conflicting payloads, crash/restart recovery, retry exhaustion, database failover, and backup restoration.

## Release status
The shared foundation is implemented, but this service is not production-ready until the service-specific work above, integration tests, and security review are complete.