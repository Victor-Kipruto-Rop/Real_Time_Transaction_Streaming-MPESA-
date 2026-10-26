# Incident Management Service — Operations and Recovery

This is a scaffold, not a declaration of production readiness.

## Required before production
- Implement a durable adapter with tenant-scoped queries, unique idempotency constraints and transactional state transitions.
- Verify service identity and authorization at the trust boundary; never trust tenant IDs supplied by untrusted request bodies.
- Add durable inbox/outbox, explicit acknowledgement boundaries, persisted retry schedules, dead-letter handling and authorized replay.
- Bound payload size, concurrency, connection pools, retry counts, deadlines and retention.
- Add dependency-backed readiness checks, SLO dashboards, alert rules, backup/restore evidence and incident runbooks.
- Test duplicate delivery, crash after persistence, dependency outages, poison messages, cross-tenant access and replay authorization.

## Recovery
Never acknowledge work before required durable state exists. Retry only transient failures with bounded backoff; quarantine permanent and security failures. Replay must preserve original event identity and create an audit record. Never log secrets or full sensitive payloads.

TELIXO does not initiate, confirm, refund, reverse, settle or transfer funds.