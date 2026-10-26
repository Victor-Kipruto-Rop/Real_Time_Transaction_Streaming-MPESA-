# TELIXO Elixir Services — Production Prompt Index

Read [ARCHITECTURE.md](ARCHITECTURE.md), the root Mix/Compose configuration and the selected service README before changing code. Use each service-specific `PROMPT.md` as a strict engineering contract.

- [Webhook Delivery](services/webhook-delivery/PROMPT.md) — outbound webhook delivery, signature safety, SSRF protection, durable retries and replay.
- [Notification Service](services/notification-service/PROMPT.md) — consent-aware notification dispatch and accurate delivery states.
- [Workflow Orchestrator](services/workflow-orchestrator/PROMPT.md) — durable state machines, idempotency and crash recovery.
- [Audit Event Service](services/audit-event-service/PROMPT.md) — durable, append-only audit ingestion.
- [Compliance Workflow](services/compliance-workflow-service/PROMPT.md) — evidence-based cases, reviews and auditable transitions.
- [Data Export](services/data-export-service/PROMPT.md) — secure asynchronous exports, scoped downloads and artifact retention.
- [Fraud Detection](services/fraud-detection/PROMPT.md) — explicitly bounded signal enrichment; no competing risk scoring.
- [Risk Engine](services/risk-engine/PROMPT.md) — adapter/coordination only where needed; Python owns canonical risk inference.
- [Integration Health](services/integration-health-service/PROMPT.md) — allowlisted, SSRF-resistant health checks.
- [Incident Management](services/incident-management-service/PROMPT.md) — controlled incident lifecycle and audited operations.

## Platform-wide rules
1. Java owns identity/control-plane and inbound provider callback intake where assigned; Python owns data processing, reconciliation matching and risk inference; Go owns event relay, quota enforcement and infrastructure monitoring; Elixir owns outbound webhook delivery and notification execution where configured. Confirm current contracts before changing boundaries.
2. TELIXO does not initiate, confirm, refund, reverse, settle or transfer funds. A callback or HTTP success is not proof of settlement.
3. Design for at-least-once delivery with stable event IDs, durable state, idempotent effects and explicit retry/dead-letter/replay policy. Do not claim exactly-once behavior without end-to-end proof.
4. Use OTP supervision deliberately, but never treat process memory as the only durable business state. Bound queues, mailboxes, tasks, concurrency, payloads and network calls.
5. Derive tenant context from trusted identity; test cross-tenant access for every data operation, replay and export.
6. Secrets must never enter source, logs, test fixtures or responses. Production configuration must reject insecure defaults.
7. Run formatting, compilation with warnings as errors where practical, unit/integration/security/fault tests and dependency checks. Report actual results and residual risks.
8. Prompts define the required engineering approach; they do not prove that existing runtime code already meets it. No production deployment or merge without explicit authorization.
