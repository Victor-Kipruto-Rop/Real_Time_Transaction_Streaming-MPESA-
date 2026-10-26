# Secure asynchronous exports and temporary artifact lifecycle — Service-Specific Engineering Prompt

# TELIXO Elixir Services — Strict Production Engineering Contract

Act as a principal Elixir/OTP engineer and security reviewer. Inspect the actual service, Mix project, dependency versions, supervision tree, config/runtime.exs, schemas, migrations, message contracts, deployment wiring and tests before changing anything. Do not assume a feature exists from this prompt alone.

## Platform invariants
- Elixir owns outbound webhook delivery, notification execution and selected durable workflow/event-consumer services only where current architecture assigns ownership. Java owns identity/control-plane and inbound provider callback intake; Python owns data processing, reconciliation matching and risk inference; Go owns event relay, quota enforcement and infrastructure monitoring. Do not create duplicate owners or competing sources of truth.
- TELIXO is not a money-movement system. Do not initiate, confirm, refund, reverse, settle or transfer funds. Delivery acknowledgements and provider callbacks are not proof of settlement.
- Tenant context must come from trusted, authenticated service claims, never an untrusted payload field. Authorize tenant-scoped reads, writes, replay, exports and administrative actions.
- Design for at-least-once message delivery. Use durable inbox/outbox or equivalent, stable event IDs, idempotent effects, explicit acknowledgements and replayable dead letters. Never claim exactly-once delivery without proof. Never acknowledge a message before the required durable state exists.
- Use OTP supervision intentionally: isolate failures, define restart intensity, avoid restart loops and distinguish transient from permanent failures. Supervised processes must not be the sole storage for durable business state.
- Bound every queue, mailbox, task, connection pool, payload, retry loop and network operation. Use back-pressure and controlled concurrency; do not spawn unbounded Tasks or create atoms from untrusted input.
- Runtime configuration must validate required production secrets and endpoints at startup. Never commit secrets, log credentials, signature secrets, raw sensitive payloads or personal data. Use TLS, least privilege, secret rotation and safe redaction.
- Validate schemas and content types; defend against SSRF, DNS rebinding, unsafe redirects, decompression bombs, oversized payloads and unsafe deserialization. Use allowlists and network egress controls where outbound requests occur.
- Use structured logs, trace/correlation IDs, metrics and separate liveness/readiness. Never put tenant IDs, event IDs, arbitrary URLs, emails or secrets in metric labels. Do not expose internal topology or exception details to public callers.
- Use explicit Ecto transactions/constraints where applicable, migrations as schema truth, and safe deploy/rollback procedures. Do not rely on in-memory state for delivery guarantees.
- Test unit behavior, real persistence/queue boundaries, tenant isolation, duplicate and out-of-order messages, concurrency, timeouts, process crashes, dependency outage, recovery, replay and shutdown. Run formatter, compiler with warnings as errors where practical, tests and dependency/security checks; report actual outputs.
- Do not deploy, change production resources, rotate live secrets or merge without explicit authorization.

## Required workflow
1. Inventory the current behavior, contracts, ownership boundaries, trust boundaries and failure modes.
2. Define state transitions, acknowledgement boundary, idempotency key, retry classification, retention and recovery before implementation.
3. Make the smallest complete compatible change; version contracts where compatibility changes.
4. Add negative and fault-injection tests, including crash-after-persist/before-ack and duplicate delivery.
5. Run `mix format --check-formatted`, `mix compile --warnings-as-errors`, `mix test`, and applicable integration/security checks; report exact commands and real results.
6. Update README, config reference, runbook, dashboards/alerts and rollback guidance.
7. Distinguish implemented, tested, unverified and residual risks. Do not label the service production-ready based on compilation alone.

## Service-specific requirements

Generate exports from authorized tenant-scoped queries with snapshot/watermark metadata, bounded row count, query timeout, memory/disk limits and cancellation. Use asynchronous durable job state for large exports; do not keep the only job state in a process. Encrypt artifacts at rest, use private object storage and short-lived authorized downloads, and delete artifacts according to retention policy. Prevent CSV formula injection and unsafe HTML/PDF rendering. Validate requested columns and date ranges; redact fields by role. Do not log exported rows or expose public permanent URLs. Test cross-tenant export access, job replay, worker crash, oversized export, cancellation, stale snapshots, formula injection, expiry and cleanup failure.

## Completion gate

Demonstrate the service's unique responsibility, enforced authorization, bounded resource usage, durable recovery and tested failure behavior. If current code conflicts with this prompt, document the conflict and propose a compatible migration; do not silently create a second source of truth.