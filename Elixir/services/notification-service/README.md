# Notification Service

**Purpose:** Email/SMS/in-app notification orchestration, preferences, templates, provider adapters and delivery status.

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


## Persisted notification policy gate

The `002_notification_policy_records.sql` migration adds tenant-scoped consent, channel-preference, and recipient-suppression records. `Persistence.PolicyStore` reads those authoritative PostgreSQL rows and applies `Domain.DispatchPolicy`; the public record-create request cannot supply a policy context or self-assert consent. A notification intent must include its requested `purpose`, and absent consent, revoked consent, disabled channels, suppressed recipients, or unavailable policy storage fail closed.

Trusted internal adapters may update policy records through `PolicyStore.record_consent/6`, `set_preference/5`, `suppress/4`, and `unsuppress/3`. These mutation functions are not exposed as public routes. Each policy mutation writes a notification-service outbox event in the same database transaction.

This gate is enforced before a notification record is queued. Provider dispatch adapters are not yet part of this service implementation; when they are added, they must re-check current consent and suppression at send time and serialize revocation/preference changes with dispatch. Do not claim provider delivery or full race-free consent enforcement until that worker and its concurrency tests are implemented.
