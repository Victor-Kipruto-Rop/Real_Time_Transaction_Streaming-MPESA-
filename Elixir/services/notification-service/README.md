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


## Notification dispatch policy gate (implementation in progress)

`Domain.DispatchPolicy` provides a fail-closed policy decision for a notification intent using a policy context loaded by a trusted internal adapter. It rejects missing consent records, ungranted consent, missing consent purpose, disabled channel preferences, and suppressed recipients. The policy context must **not** be accepted from the public request body.

This module is a tested policy primitive, not yet an end-to-end enforcement guarantee. The notification record controller currently validates and persists generic records; a durable consent/preference/suppression data owner and an authenticated adapter must be wired into dispatch before notifications may be sent. Do not claim consent enforcement or production readiness until that integration and its race-condition tests are complete.
