# Elixir service implementation status

The ten standalone Elixir applications now have a shared implementation baseline for authenticated tenant-scoped record APIs.

## Implemented in this change
- HS256 JWT verification with signature, issuer, audience, expiry and not-before checks; API routes fail closed when the signing secret is missing.
- PostgreSQL-backed record storage with tenant-scoped reads, idempotency uniqueness, guarded state transitions and startup schema initialization.
- Authenticated create/read/state-transition endpoints in each service.
- Database-backed readiness checks; liveness does not claim dependencies are ready.
- Versioned event validation, service-specific command validation, bounded retry classification and tests.
- SQL schema artifacts and operations guidance.

## Required deployment configuration
- Set DATABASE_URL and JWT_SECRET (at least 32 bytes) through the deployment secret manager.
- Set JWT_ISSUER to the trusted issuer; tokens must contain tenant_id, sub, iss, aud and exp.
- The audience accepted by this service boundary is telixo.
- Run database backup/restore tests and validate schema privileges before production.

## Remaining production gates
- Add durable outbox/inbox and service-specific workers, delivery/provider adapters, retry scheduling, dead-letter and authorized replay workflows.
- Add database connection pooling, migrations with version tracking, retention policies, secrets rotation/key IDs, audit integration, rate limits, tracing and dependency-backed integration/fault-injection tests.
- Validate every service state machine against product contracts. This common record API is not a substitute for each service's complete business workflow.
- Do not route production traffic until CI and security review pass.
