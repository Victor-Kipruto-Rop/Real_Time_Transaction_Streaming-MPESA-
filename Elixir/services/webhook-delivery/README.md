# Webhook Delivery

**Purpose:** Tenant webhook subscriptions, HMAC signing, bounded retries, replay protection and delivery history. Must not publish duplicate delivery attempts as separate business events.

## Current scaffold

Standalone Phoenix application with an OTP supervision tree, JSON health/readiness routes, runtime configuration and telemetry hooks.

## HMAC delivery signing foundation

`PesaGuard.WebhookDelivery.Signing` generates versioned HMAC-SHA256 signatures over
`timestamp <> "." <> exact_request_body_bytes`. It emits `x-telixo-delivery-id`,
`x-telixo-timestamp`, and `x-telixo-signature: v1=<lowercase-hex>` headers.
Secrets shorter than 32 bytes are rejected. Receivers should verify the signature
against the raw body before JSON parsing and enforce the five-minute default
timestamp tolerance.

A timestamp window limits stale requests; it is **not** durable replay protection.
The receiving system must persist delivery IDs/idempotency keys and reject IDs
already accepted. The `PesaGuard.WebhookDelivery.DeliveryRequest` module validates a target and builds a signed request envelope with a stable delivery ID for a subscription/event pair. It deliberately performs no network I/O and writes no delivery state. This is not yet the complete subscription-management or customer-delivery pipeline.

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


## Durable customer webhook delivery

The authenticated API now supports:

- `POST /v1/subscriptions` — create a tenant-owned HTTPS subscription with `target_url`, a list of `event_types`, and a signing `secret` (minimum 32 bytes). The response never returns the secret.
- `GET /v1/subscriptions` — list subscriptions for the authenticated tenant only.
- `POST /v1/events` — enqueue an event with `event_id`, `event_type`, integer `schema_version`, and object `payload`. The tenant comes from the verified JWT; a supplied conflicting tenant is rejected. Enqueue is transactional across matching subscriptions and idempotent per subscription/event.
- `GET /v1/deliveries/:id` — read tenant-scoped delivery metadata and status without exposing payloads or signing secrets.

The customer delivery queue is separate from the internal transactional-outbox relay. The supervised dispatcher is opt-in via `WEBHOOK_DELIVERY_WORKER_ENABLED=true`, claims durable work using PostgreSQL row locks and leases, signs the exact request body, disables redirects, verifies TLS certificates, and retries transient failures with bounded backoff before dead-lettering. A deterministic delivery ID is sent to consumers for their own durable deduplication. Delivery is at-least-once; consumers must deduplicate by `x-telixo-delivery-id`.

Signing secrets are encrypted at rest with AES-256-GCM. Configure `WEBHOOK_ENCRYPTION_KEY` as base64-encoded 32-byte key material from a secret manager. Rotate this key only with a documented re-encryption plan. Restrict outbound network egress to prevent DNS rebinding or private-address SSRF; application URL checks alone are not a complete network boundary.

These changes still require successful Elixir CI, PostgreSQL integration tests, concurrency/failure injection, and deployment-specific egress controls before production use.


## Durable customer webhook delivery

Authenticated endpoints:

- `POST /v1/subscriptions`: create a tenant-owned HTTPS subscription with `target_url`, `event_types`, and a signing secret of at least 32 bytes. The secret is never returned.
- `GET /v1/subscriptions`: list only the authenticated tenant's subscriptions.
- `POST /v1/events`: enqueue an event containing `event_id`, `event_type`, integer `schema_version`, and object `payload`. The tenant is taken from the verified JWT. Fan-out is transactional and idempotent per subscription/event.
- `GET /v1/deliveries/:id`: read tenant-scoped delivery status without exposing payloads or signing secrets.

The customer queue is separate from the internal transactional-outbox relay. Its supervised dispatcher is opt-in via `WEBHOOK_DELIVERY_WORKER_ENABLED=true`; it uses PostgreSQL leases and row locks, signs exact request bytes, disables redirects, verifies TLS certificates, retries transient errors with bounded backoff, and dead-letters exhausted/permanent failures. Delivery is at-least-once, so consumers must durably deduplicate by `x-telixo-delivery-id`.

Signing secrets are encrypted at rest using AES-256-GCM. Configure `WEBHOOK_ENCRYPTION_KEY` as base64-encoded 32-byte key material from a secret manager. Key rotation needs a documented re-encryption plan. Restrict outbound network egress to prevent DNS rebinding and private-address SSRF; URL checks alone are not a complete network boundary.

Successful Elixir CI, PostgreSQL integration tests, fault injection, and deployment egress controls remain required before production use.
