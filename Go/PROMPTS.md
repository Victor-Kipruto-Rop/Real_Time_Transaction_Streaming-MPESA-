# Go Services — Engineering Prompt Index

These prompts are service-specific implementation contracts for engineers and coding agents working under `Go/services/`. Read the matching prompt before modifying a service.

- [Event Relay](services/event-relay/PROMPT.md) — transactional outbox delivery, at-least-once semantics, leases, retries, dead letters, consumer idempotency and broker recovery.
- [Quota Engine](services/quota-engine/PROMPT.md) — trusted gateway context, atomic Redis quotas, environment isolation, fail-closed behavior and policy authority.
- [Infrastructure Monitor](services/infrastructure-monitor/PROMPT.md) — SSRF-resistant dependency checks, bounded concurrency, freshness-aware health and private topology protection.

## Rules that apply to every Go service

1. **Inspect before editing.** Read the implementation, tests, schemas, migrations, Compose files and service README. Identify existing contracts and risks before proposing a rewrite.
2. **Preserve ownership boundaries.** Go owns infrastructure event relay, quota enforcement and infrastructure monitoring. Do not duplicate Java's gateway/identity/payment APIs, Python's ingestion/reconciliation/risk domain, or Elixir's webhook delivery/notification workflows.
3. **No money movement.** No Go service may initiate, confirm, reject, reverse, refund, settle or move funds. Risk and quota decisions are not payment authorization.
4. **Secure defaults.** Least privilege, private networking, TLS, managed and rotated secrets, strict input validation, bounded resource use, safe errors and no sensitive data in logs.
5. **Reliability is explicit.** State delivery/consistency guarantees, timeout behavior, retries, idempotency, recovery paths and failure semantics. Never claim exactly-once delivery without proof across every boundary.
6. **Test failures, not just happy paths.** Include concurrency, cancellation, malformed input, dependency outage, partial failure, process restart and migration compatibility. Use disposable test dependencies only.
7. **Observable but private.** Structured logs, useful metrics and trace/correlation context are required. Avoid high-cardinality labels and exposing internal topology or payloads.
8. **Production config must fail fast.** Validate required environment variables and unsafe defaults at startup. Local development credentials must not be accepted in production.
9. **Compatibility and rollout.** Document schema/API changes, forward/rollback migration steps, staging validation and rollback criteria. Do not route production traffic merely because a container builds.
10. **Evidence-based completion.** Run `gofmt`, service tests, `go test -race`, `go vet`, and relevant integration/Compose checks. Report actual results, untested areas and residual risks. Never invent successful commands or claim readiness based on compilation alone.

## Required response from a coding agent

Before implementation: summarize scope, current behavior, invariants, assumptions, failure modes and planned tests.

After implementation: list files changed, design decisions, exact test commands/results, migration and deployment notes, rollback steps, known gaps, and a clear readiness assessment. Separate verified facts from proposed follow-up work.
