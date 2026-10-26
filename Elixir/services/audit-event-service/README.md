# Audit Event Service

**Purpose:** Durable append-oriented audit event intake, integrity metadata, controlled access and retention integration.

## Current scaffold

Standalone Phoenix application with an OTP supervision tree, JSON health/readiness routes, runtime configuration and telemetry hooks.

## Required before production

- Implement business handlers, explicit API/event contracts and domain-specific tests.
- Add OIDC/JWT verification or authenticated internal service identity; health routes must not expose sensitive data.
- Define tenant context and authorization for every tenant-facing operation.
- Add persistence and migrations only where required, with a documented data owner and least-privilege database role.
- For asynchronous workflows, implement durable inbox/outbox, idempotency, bounded retries, durable DLQ and audited replay.
- Add broker/database adapters, dependency-aware readiness, metrics exporter, tracing, dashboards, alerts, SLOs and runbooks.
- Apply request-size/rate limits, safe logging, secret rotation, dependency/SBOM scanning and graceful shutdown.
- Test restart recovery, duplicate events, poison messages, timeouts and downstream outages.

The current endpoints are scaffold health checks, not proof of domain implementation or production readiness.


## Append-only audit ledger

Audit-event writes use a dedicated PostgreSQL ledger instead of the mutable generic record state machine. Each tenant has a serialized sequence and SHA-256 hash chain; appends, tenant-head updates, and audit-event-service.audit_event_appended outbox insertion commit in one transaction. Idempotency keys return the original event for identical retries and conflict if reused for a different event. The database migration blocks row updates/deletes through append-only rules, and AuditLedger.verify_chain/1 checks sequence, previous-hash linkage and event hashes.

The hash chain provides tamper-evidence within the database trust boundary; it is not a substitute for external/WORM backups, privileged-role separation, retention controls, or independent periodic verification. The generic state-transition endpoint is disabled for audit events. CI and PostgreSQL integration tests must pass before promotion.
