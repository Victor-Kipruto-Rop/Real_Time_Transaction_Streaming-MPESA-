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
