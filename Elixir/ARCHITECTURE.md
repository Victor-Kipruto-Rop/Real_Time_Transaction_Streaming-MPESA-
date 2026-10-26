# Elixir / Phoenix architecture and production boundaries

## 1. Webhook Delivery
Path: `services/webhook-delivery/`

Tenant webhook subscriptions, HMAC signing, bounded retries, replay protection and delivery history. Must not publish duplicate delivery attempts as separate business events.

## 2. Notification Service
Path: `services/notification-service/`

Email/SMS/in-app notification orchestration, preferences, templates, provider adapters and delivery status.

## 3. Risk Engine
Path: `services/risk-engine/`

Low-latency risk signal evaluation and explainable risk assessments; never autonomously reverse payments or move funds.

## 4. Fraud Detection
Path: `services/fraud-detection/`

Streaming anomaly feature evaluation and fraud case signals using versioned rules; integrate with the canonical risk decision boundary.

## 5. Audit Event Service
Path: `services/audit-event-service/`

Durable append-oriented audit event intake, integrity metadata, controlled access and retention integration.

## 6. Workflow Orchestrator
Path: `services/workflow-orchestrator/`

Long-running onboarding, review and operational workflows with durable state, retries, timeouts and idempotent transitions.

## 7. Integration Health Service
Path: `services/integration-health-service/`

Provider dependency health, circuit state and operational diagnostics; must not expose credentials or sensitive response bodies.

## 8. Data Export Service
Path: `services/data-export-service/`

Authorized asynchronous report/export jobs, scoped artifact access, expiry and audit trail.

## 9. Compliance Workflow Service
Path: `services/compliance-workflow-service/`

Compliance case routing, evidence requests, retention and policy workflow coordination; no fabricated verification results.

## 10. Incident Management Service
Path: `services/incident-management-service/`

Internal incident lifecycle, alert acknowledgement, escalation metadata and operational postmortem tracking.

## Runtime standards

- One independent Mix project and release boundary per service.
- OTP supervision trees must supervise the endpoint and telemetry; add workers only with explicit restart, backoff and shutdown policies.
- Read secrets at runtime from the deployment secret store. Fail closed on missing production secrets.
- Keep health/readiness endpoints minimal and never reveal stack traces, dependency credentials or tenant data.
- Use authenticated service identities, tenant-scoped authorization, schema validation, request-size limits and rate limits.
- For durable asynchronous work, persist intent before acknowledging; use outbox/inbox or equivalent guarantees, idempotency keys, bounded retries and a durable DLQ/replay workflow.
- Use versioned event schemas, correlation/trace IDs, UTC timestamps and decimal strings or integer minor units for money.
- Apply least privilege to database and broker identities; never access another service's private tables.
- Add telemetry, SLOs, alerts, graceful shutdown, resource limits, dependency scanning and a tested rollback/runbook before production.
