# Production security and reliability gates

This checklist is not a claim the current scaffolds satisfy it.

## Edge and identity
- [ ] TLS, managed certificates, WAF, request-size limits, throttling and abuse protection.
- [ ] OIDC issuer/audience validation, short-lived tokens, key rotation and MFA for privileged users.
- [ ] Default-deny server-side RBAC/ABAC and tests for cross-tenant denial.
- [ ] Strip spoofable identity/tenant headers at the edge.
- [ ] Environment-specific CORS, CSP, secure-cookie/CSRF controls where applicable.
- [ ] Separate sandbox/production URLs, credentials, data, quotas and access.

## Data and event reliability
- [ ] Exactly one authoritative transaction store is designated.
- [ ] Service-owned data boundaries, tenant isolation and tested backups/restores.
- [ ] Transactional outbox, durable inbox/deduplication and replay.
- [ ] Durable DLQ, poison-message recovery, retry budgets, alerts and permissioned replay.
- [ ] Versioned event contracts and schema compatibility checks.
- [ ] No provider credentials or tokens in events/logs.

## Operations
- [ ] Liveness/readiness semantics documented and tested.
- [ ] SLOs, dashboards, alerts and runbooks reviewed.
- [ ] Correlation IDs propagate across gateway, APIs, broker and workers.
- [ ] Logs are structured, redacted, access-controlled and retained by policy.
- [ ] Secret manager, key rotation, least-privilege service identities and audit trail.
- [ ] Restore, rollback, incident response, load and failure-injection tests pass in staging.
- [ ] Status site uses real monitoring data and visibly reports monitoring gaps.

PesaGuard reconciles supported provider events against internal records and flags discrepancies. It must not imply reconciliation authorizes payment initiation, confirmation, refund, money movement or settlement.
