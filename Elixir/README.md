# PesaGuard Elixir / Phoenix Services

Independent Elixir/OTP and Phoenix applications for concurrency-heavy, asynchronous and workflow-oriented PesaGuard workloads. Each service is a standalone Mix project under `services/` (not a single umbrella release), so it can be tested, built, configured and deployed independently.

## Docker

Build and start the ten standalone service containers locally (ports 8200–8209):

```bash
docker compose -f Elixir/compose.yaml up -d --build
docker compose -f Elixir/compose.yaml ps
```

Use the root `compose.yaml` to combine Elixir with the shared dependencies and other PesaGuard platforms. See [`DOCKER_PLATFORM.md`](../DOCKER_PLATFORM.md). Development credentials are not production secrets, and endpoint/integration behavior still needs service-level validation.

## Requirements

- Elixir 1.17+ and Erlang/OTP 27+ recommended.
- Each app uses Phoenix 1.7, Plug Cowboy and Jason.
- CI fetches dependencies and runs `mix test` for every service.
- Configure `SECRET_KEY_BASE` with a strong secret from your deployment secret manager. The development default must never be used for production.
- Configure `PHX_HOST`, `PORT`, TLS termination, trusted proxy policy, telemetry export and deployment-specific secrets.

## Service catalog

- **Webhook Delivery** — `services/webhook-delivery/`: Tenant webhook subscriptions, HMAC signing, bounded retries, replay protection and delivery history. Must not publish duplicate delivery attempts as separate business events.
- **Notification Service** — `services/notification-service/`: Email/SMS/in-app notification orchestration, preferences, templates, provider adapters and delivery status.
- **Risk Engine** — `services/risk-engine/`: Low-latency risk signal evaluation and explainable risk assessments; never autonomously reverse payments or move funds.
- **Fraud Detection** — `services/fraud-detection/`: Streaming anomaly feature evaluation and fraud case signals using versioned rules; integrate with the canonical risk decision boundary.
- **Audit Event Service** — `services/audit-event-service/`: Durable append-oriented audit event intake, integrity metadata, controlled access and retention integration.
- **Workflow Orchestrator** — `services/workflow-orchestrator/`: Long-running onboarding, review and operational workflows with durable state, retries, timeouts and idempotent transitions.
- **Integration Health Service** — `services/integration-health-service/`: Provider dependency health, circuit state and operational diagnostics; must not expose credentials or sensitive response bodies.
- **Data Export Service** — `services/data-export-service/`: Authorized asynchronous report/export jobs, scoped artifact access, expiry and audit trail.
- **Compliance Workflow Service** — `services/compliance-workflow-service/`: Compliance case routing, evidence requests, retention and policy workflow coordination; no fabricated verification results.
- **Incident Management Service** — `services/incident-management-service/`: Internal incident lifecycle, alert acknowledgement, escalation metadata and operational postmortem tracking.

## Cross-language boundaries

- Python remains the existing streaming/callback ingestion implementation until a separately reviewed migration says otherwise.
- Java owns the Java service contracts described under `Java/`; do not implement a second authoritative transaction ledger in Elixir.
- Elixir services should consume versioned events and use authenticated internal APIs. They must not write directly to another service's private tables.
- The canonical transaction owner must be chosen by auditing the existing PesaGuard backend before enabling any write path.
- Reconciliation outcomes and risk signals must not be confused with payment execution, reversals or settlement.

## Security and production gates

The services provide initial Phoenix endpoints, configuration hooks and smoke tests; they are **not automatically production-ready**. Before exposure, implement domain handlers, authorization, event/database adapters, migrations where needed, idempotency, bounded retries, durable dead-letter/replay, observability, rate limits, resource budgets, dependency scanning, SBOM, backup/restore and runbooks. Set production secrets securely and restrict management endpoints. Never log API keys, access tokens, PINs, callback secrets or sensitive payloads.

## Service engineering prompts

Use [PROMPTS.md](PROMPTS.md) and the matching service-level `PROMPT.md` before implementing or refactoring an Elixir service. These prompts define service ownership, OTP reliability, security, durable delivery, test requirements and completion gates.
