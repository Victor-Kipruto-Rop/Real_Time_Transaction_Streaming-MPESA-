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


## Privileged retention controls and independent verification

Migration `002_audit_controls.sql` adds tenant-scoped retention-policy metadata, an append-only privileged-access log, and append-only integrity-verification run records. The `/v1/admin/retention-policy` endpoints and online integrity-verification endpoint require a verified JWT containing an explicit `audit_admin`, `audit_compliance`, or `platform_security_admin` role plus an `x-audit-reason` header. Every privileged read/write is recorded with actor, tenant, reason, and request ID.

Retention policies and legal holds are persisted and enforced by `mix telixo.audit.retention`. The task is dry-run by default and only executes when `AUDIT_RETENTION_EXECUTE=true`. It requires `AUDIT_RETENTION_DATABASE_URL` using the dedicated `telixo_audit_retention_executor` database role, `AUDIT_ARCHIVE_DIRECTORY` mounted on encrypted immutable/WORM-backed storage, `AUDIT_RETENTION_ACTOR`, and an explicit `AUDIT_RETENTION_REASON`. It archives a contiguous expired prefix as JSONL, verifies the written SHA-256 digest, records an immutable archive manifest, advances a chain anchor, writes privileged-access history, and deletes only after all checks pass in one database transaction. Legal holds prevent purge. The database migration suppresses normal deletes and only permits the dedicated role with a transaction-local retention authorization marker. A DBA must provision the executor role with the minimum required table privileges; do not grant this role to the application runtime.

For independent verification, schedule `mix telixo.audit.verify` from this service directory. It requires `AUDIT_VERIFY_DATABASE_URL` for a dedicated read-only database role and `DATABASE_URL` for writing verification results. The task rejects identical database usernames, independently recomputes retained-chain hashes from the last archive anchor, verifies every archived file against its manifest hash, records append-only verification results, and exits unsuccessfully on any chain or archive mismatch. Schedule it externally (for example, with a controlled cron job) and alert on non-zero exit status or failed verification rows.
