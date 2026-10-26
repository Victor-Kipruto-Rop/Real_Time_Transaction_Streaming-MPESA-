# Elixir platform implementation status

## Implemented foundation

All ten standalone Elixir/Phoenix applications now include:
- Authenticated API routes using HS256 bearer JWT verification with tenant, subject, issuer, audience, expiry, not-before, token-size, and signature checks.
- PostgreSQL-backed tenant-scoped record reads and writes, unique idempotency keys, conflicting-payload detection, optimistic state transitions, and startup schema initialization.
- Transactional outbox events for record creation and state transitions, leased batch claiming, lease-expiry recovery, bounded retries, dead-lettering, and an HTTPS relay with certificate verification.
- Deterministic service-specific request processors for initial validation/scoring rules and unit tests for those contracts.
- Liveness/readiness endpoints, operations documentation, Compose wiring, and release-gate guidance.

## Required runtime configuration

Production requires DATABASE_URL, JWT_SECRET (at least 32 bytes), EVENT_RELAY_URL (HTTPS), EVENT_RELAY_TOKEN (at least 32 bytes), SECRET_KEY_BASE, and PHX_HOST. Tokens must carry tenant_id, sub, iss, aud, and exp; the default issuer and audience are telixo. Secrets must be injected by a secret manager.

## Not yet production-ready

- The API currently exposes a shared generic record resource. Service-specific business endpoints, workers, timers, provider adapters, and lifecycle orchestration are incomplete.
- The outbox relay assumes the receiver durably accepts events before returning 2xx and deduplicates by Idempotency-Key. End-to-end receiver integration tests are still required.
- Add asymmetric JWT/JWKS verification or a reviewed key-rotation design, rate limits, strict request-size limits, per-service authorization scopes, audit integration, and security review.
- Versioned SQL migrations now run at service startup with per-service migration versions and SHA-256 checksums; applied migration files are immutable. Least-privilege DB roles, connection recovery, backups/restores, retention, and upgrade/rollback procedures still require deployment-level validation.
- Add integration/fault-injection tests for tenant isolation, concurrent idempotency, conflicting retries, process crashes, expired leases, relay outages, permanent errors, dead-letter replay, and data recovery.
- The GitHub Actions runs currently report failures, but the connected tooling has not exposed their job steps/log artifacts. Compilation and tests are therefore not verified.

Do not deploy production traffic until these gaps are closed and CI passes. TELIXO does not initiate, confirm, refund, reverse, settle, or transfer funds.