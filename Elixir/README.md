# TELIXO Elixir / Phoenix Services

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


## Authenticated API and durable outbox

Each service exposes liveness at `GET /health`, database-backed readiness at `GET /ready`, and authenticated tenant-scoped record endpoints under `/v1/records`. API requests require a bearer JWT signed with HS256. Claims must include `tenant_id`, `sub`, `iss`, `aud`, and `exp`; the default issuer and audience are `telixo`. Set `JWT_SECRET` to at least 32 bytes and align `JWT_ISSUER` with the trusted issuer.

Record creation and state changes write an event to PostgreSQL's transactional outbox in the same transaction. The outbox relay delivers events at least once to the configured `EVENT_RELAY_URL` using `EVENT_RELAY_TOKEN`; the receiver must durably accept events and deduplicate by the `Idempotency-Key` header. Delivery attempts are leased, retried with bounded backoff, and dead-lettered after repeated or permanent failures.

The Compose stack now includes a PostgreSQL container. Before starting it, provide `ELIXIR_POSTGRES_PASSWORD`, `SECRET_KEY_BASE`, `JWT_SECRET`, `EVENT_RELAY_URL`, and `EVENT_RELAY_TOKEN` in the environment. Never use development placeholders for production secrets. The shared record API and outbox are a common foundation; service-specific business handlers and external-provider adapters still require service-level integration tests.


## Service-specific validation modules

Each service exposes a Domain.Processor used by its authenticated record API:
- Webhook Delivery rejects non-HTTPS destinations, URL credentials, non-standard ports and literal IP hosts. Network egress controls are still required to prevent DNS-based SSRF.
- Notification Service validates supported channels and recipient references.
- Workflow Orchestrator validates workflow identifiers and positive integer versions.
- Audit Event Service validates actor types, action length and ISO-8601 timestamps.
- Compliance Workflow validates evidence reference lists and duplicate evidence references.
- Fraud Detection produces a bounded, explainable rule score from versioned features; it does not initiate or reverse payments.
- Risk Engine aggregates normalized signals into a low/medium/high assessment and explanation list; it does not perform payment actions.
- Integration Health validates check types and bounded timeouts.
- Incident Management validates severity, summary length and timestamps.
- Data Export validates formats, scopes and row limits.

These modules implement deterministic validation and initial scoring contracts. They do not replace provider-specific delivery adapters, actual health probes, export execution, workflow timers, external audit retention, or a model-serving deployment. Those require integration tests and service-specific operational configuration before production use.


The outbox relay requires an HTTPS endpoint and verifies TLS certificates before sending bearer credentials. The relay processes bounded batches and reclaims expired leases after a worker crash.


## Release gate

Before promotion, run `mix format --check-formatted`, `MIX_ENV=test mix compile --warnings-as-errors`, and `mix test` inside every service directory. Then run PostgreSQL-backed integration tests for duplicate idempotency keys, conflicting payloads, tenant isolation, concurrent transitions, outbox lease expiry, retry exhaustion, permanent HTTP failures, and relay crash recovery. The current unit suite does not replace these integration tests.


Deployment passwords used in DATABASE_URL should be URL-safe (letters, digits, and hyphens are recommended) unless the connection string is percent-encoded correctly.
