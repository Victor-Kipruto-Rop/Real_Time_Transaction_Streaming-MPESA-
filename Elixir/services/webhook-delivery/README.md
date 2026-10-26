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

## Durable customer webhook delivery (implementation in progress)

- Tenant-scoped subscriptions and delivery records are persisted in PostgreSQL with unique idempotency constraints.
- Subscription secrets are encrypted with AES-256-GCM. Configure `WEBHOOK_SECRET_ENCRYPTION_KEY` as base64 for exactly 32 random bytes using a secret manager; do not commit it. Key rotation needs an explicit operational migration.
- The authenticated API exposes `GET /v1/subscriptions`, `POST /v1/subscriptions`, `POST /v1/subscriptions/:subscription_id/deliveries`, `GET /v1/subscriptions/:subscription_id/deliveries`, `GET /v1/subscriptions/:subscription_id/deliveries/:delivery_id/attempts`, and `POST /v1/events`. Attempt-history reads are tenant- and subscription-scoped. Supply an `Idempotency-Key` when creating a subscription. The event endpoint fans out to active subscriptions matching the event type; retry the same event ID after partial failures to complete missing per-subscription deliveries.
- A supervised worker leases pending deliveries, signs the exact HTTP body, disables redirects, verifies TLS peers, applies DNS destination checks, and records delivery/retry/dead-letter state. Delivery is at least once; receivers must deduplicate `x-telixo-delivery-id`.
- Each completed delivery attempt is recorded transactionally with its attempt number, outcome, HTTP status (when present), and sanitized error code. Retry scheduling uses capped exponential backoff with jitter; exhausted or permanent failures are dead-lettered. Attempt history is retained separately from the delivery's current status so operators can audit retry behavior.
- The authenticated `POST /v1/events` endpoint is the integration seam for the trusted internal event relay. Source services must call it only with authenticated tenant-scoped event contracts; source-event fan-out is not a substitute for the separate transactional outbox relay.
- DNS preflight cannot eliminate DNS-rebinding races. Production network egress policy must block loopback, private, link-local, and metadata-service destinations. The delivery pipeline still requires CI and fault-injection verification before production use.
