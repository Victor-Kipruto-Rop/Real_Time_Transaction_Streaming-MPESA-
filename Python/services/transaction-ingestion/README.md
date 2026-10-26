# Transaction Ingestion Service

**Role:** consume durably accepted provider events and approved imports, normalize records into versioned internal events, enforce idempotency and publish recoverable outcomes.

## Boundaries
- Does not expose a competing public Daraja callback endpoint when Java is the configured callback owner.
- Does not own tenant identity, merchant credentials, the canonical transaction ledger or reconciliation decisions.
- Does not initiate, confirm, refund, reverse, settle or move money.
- Does not send customer webhooks or notifications; Elixir owns outbound delivery.

## Required behavior before production
- Verify internal event signature/workload identity and trusted tenant envelope.
- Validate schema version, identifiers, timestamps, amount precision and provider references.
- Use durable inbox/idempotency records and a transactional outbox or equivalent.
- Commit Kafka offsets only after durable effects succeed; distinguish duplicate, retryable, poison and transient failures.
- Route poison events to durable DLQ/quarantine with reason, attempt count, correlation ID and controlled replay.
- Expose liveness/readiness, metrics, structured logs and tracing.
- Test duplicate delivery, crashes around DB commit, broker/DB outage, malformed payloads, replay and tenant spoofing.

The canonical implementation is being migrated from `Python/ingestion/` and `Python/streaming/`. This directory defines the target boundary; it does not claim that a deployable implementation has already been moved here.
