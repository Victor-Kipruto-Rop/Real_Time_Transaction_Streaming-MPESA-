# TELIXO Java Services — Production Prompt Index

Read [ARCHITECTURE.md](ARCHITECTURE.md), the parent Maven configuration and the service README before making changes. Treat the service-specific prompt as a strict engineering contract.

- [API Gateway](services/api-gateway/PROMPT.md) — edge routing, request admission and API composition.
- [Identity Service](services/identity-service/PROMPT.md) — authentication, sessions, credentials and OAuth/OIDC.
- [Tenant Service](services/tenant-service/PROMPT.md) — tenant lifecycle and environment isolation.
- [Merchant Service](services/merchant-service/PROMPT.md) — merchant profiles and operational account records.
- [Transaction Service](services/transaction-service/PROMPT.md) — immutable provider transaction facts and safe query APIs.
- [Payment Orchestration](services/payment-orchestration-service/PROMPT.md) — approved workflow coordination without money movement.
- [Callback Management](services/callback-management-service/PROMPT.md) — authenticated inbound callbacks and durable handoff.
- [Reconciliation Service](services/reconciliation-service/PROMPT.md) — job coordination with Python-owned matching boundary.
- [Risk Service](services/risk-service/PROMPT.md) — risk assessment integration without duplicate inference.
- [Developer Portal](services/developer-portal-service/PROMPT.md) — developer projects, sandbox and production-access workflow.
- [Team Permissions](services/team-permissions-service/PROMPT.md) — membership, role and scope authorization.
- [Onboarding & KYB](services/onboarding-kyb-service/PROMPT.md) — evidence-based verification and onboarding state.
- [Integration Registry](services/integration-registry-service/PROMPT.md) — provider capabilities and secure credential references.
- [Audit Service](services/audit-service/PROMPT.md) — append-only security and workflow audit records.
- [Compliance Service](services/compliance-service/PROMPT.md) — policy evidence, retention and reporting.
- [Document Service](services/document-service/PROMPT.md) — private document storage and access control.
- [Notification Service](services/notification-service/PROMPT.md) — notification intent/preferences, with Elixir owning delivery where configured.
- [Webhook Delivery Service](services/webhook-delivery-service/PROMPT.md) — subscription metadata only when Elixir owns actual delivery.
- [Reporting Service](services/reporting-service/PROMPT.md) — tenant-scoped read models and safe exports.
- [Operations Service](services/operations-service/PROMPT.md) — audited operator workflows and incident controls.

## How to use

Give the selected `PROMPT.md` to the coding agent alongside the specific task and repository access. The prompt defines required behavior and tests; it is not evidence that the current runtime already satisfies those requirements. The agent must inspect code, tests, migrations, contracts and deployment wiring before editing.

## Cross-service invariants

1. Java owns gateway and identity/control-plane workflows only where the current architecture assigns them. Python owns data processing, reconciliation matching and risk inference; Go owns event relay, quota enforcement and infrastructure monitoring; Elixir owns outbound webhook delivery and notification execution. Confirm actual ownership and contracts before changing boundaries.
2. **No money movement.** Services must not initiate, confirm, refund, reverse, settle or transfer funds. Provider callbacks and HTTP success are observations, not proof of settlement.
3. Derive tenant identity from trusted server-side context. Authorize every tenant-owned read, write, export, job and event; test cross-tenant access.
4. Distributed effects require explicit idempotency, durable recovery and auditable state transitions. Do not promise exactly-once delivery without end-to-end proof.
5. Production config must fail fast on insecure defaults. Never commit secrets or expose them in logs, examples or API responses.
6. Run tests and report actual evidence. No production deployment, merge or live-resource changes without explicit authorization.
