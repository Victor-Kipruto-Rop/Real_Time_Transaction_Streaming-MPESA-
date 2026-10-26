# Cross-service event contract

Required envelope: immutable `event_id`, `event_type`, `schema_version`, UTC `occurred_at`, stable `producer`, `correlation_id`, optional `causation_id`, authorized `tenant_id` where applicable, and schema-validated `data`. Never include secrets, tokens, provider credentials or unnecessary personal/financial data.

## Delivery requirements
1. Persist domain state and outbox entry atomically for relational writes.
2. Mark outbox delivered only after broker acknowledgement; retry transient errors with bounded exponential backoff and jitter.
3. Deduplicate consumers using a durable inbox/idempotency key and commit the effect atomically where possible.
4. Send poison messages to durable DLQ with error classification and trace context.
5. Alert on stalled queues/partitions and provide audited, permissioned replay.
6. Acknowledge/commit only after durable handling succeeds.
7. Assume duplicates; do not promise end-to-end exactly-once across database and broker.

## Proposed topic names (not provisioned yet)
- pesaguard.transaction.normalized.v1
- pesaguard.reconciliation.result.v1
- pesaguard.risk.signal.v1
- pesaguard.webhook.delivery.requested.v1
- pesaguard.webhook.delivery.result.v1
- pesaguard.notification.requested.v1
- pesaguard.audit.event.v1
- pesaguard.integration.health.v1
- pesaguard.compliance.case.updated.v1
- pesaguard.platform.incident.v1

All frontends configure one public `VITE_API_BASE_URL` for the gateway. Never embed API private keys or consumer secrets in browser assets. Backend enforces CORS, authentication, authorization, tenant scope, rate limits and audit requirements.
