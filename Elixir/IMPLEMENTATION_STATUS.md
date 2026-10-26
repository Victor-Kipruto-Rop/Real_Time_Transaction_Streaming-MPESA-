# Elixir Platform Scaffold Status

All ten Elixir service folders now have deterministic domain validation, versioned event-envelope validation, fail-closed tenant helper contracts, bounded retry classification, repository behaviour contracts, tests and operations guidance.

This is scaffolding, not proof of production readiness. The repository behaviour has no concrete durable database adapter yet. Broker integration, authenticated service identity, migrations, durable inbox/outbox, dead-letter/replay, and provider adapters must be implemented and tested before production traffic.

- webhook-delivery — Webhook Delivery
- notification-service — Notification Service
- workflow-orchestrator — Workflow Orchestrator
- audit-event-service — Audit Event Service
- compliance-workflow-service — Compliance Workflow Service
- data-export-service — Data Export Service
- fraud-detection — Fraud Detection
- risk-engine — Risk Engine
- integration-health-service — Integration Health Service
- incident-management-service — Incident Management Service

## Validation gate
For every service, run mix format --check-formatted, mix compile --warnings-as-errors and mix test from its own directory. Then run integration and fault-injection tests against real dependency containers. Do not infer successful validation from source creation.