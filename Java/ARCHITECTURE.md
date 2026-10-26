# PesaGuard Java architecture

## 1. API Gateway
Path: `services/api-gateway/`

Routing, request correlation and gateway policy; service-level authorization remains mandatory.

## 2. Identity Service
Path: `services/identity-service/`

OIDC/SSO, MFA integration and identity lifecycle; do not store plaintext passwords.

## 3. Tenant Service
Path: `services/tenant-service/`

Tenant lifecycle, tenant metadata and trusted tenant-context resolution.

## 4. Merchant Service
Path: `services/merchant-service/`

Merchant profiles and provider-account metadata, with secrets held separately.

## 5. Merchant Onboarding and KYB
Path: `services/onboarding-kyb-service/`

Verification cases, evidence workflow and real provider adapters with pending/manual-review states.

## 6. Team and Permissions
Path: `services/team-permissions-service/`

Membership, role assignment and tenant-scoped authorization policies.

## 7. Developer Portal
Path: `services/developer-portal-service/`

Developer projects, sandbox, API-key lifecycle, usage and production-access requests; store only secret hashes.

## 8. Payment Orchestration
Path: `services/payment-orchestration-service/`

Coordinates supported payment operations and state transitions; ingestion is not execution or settlement.

## 9. Canonical Transaction
Path: `services/transaction-service/`

Proposed canonical transaction owner; audit the existing backend before enabling writes.

## 10. Reconciliation
Path: `services/reconciliation-service/`

Ledger matching and persisted reconciliation decisions.

## 11. Risk and Fraud
Path: `services/risk-service/`

Risk signals and assessments; does not independently reverse payments or settle funds.

## 12. Callback Management
Path: `services/callback-management-service/`

Provider callback configuration and registration metadata; Python remains the ingestion owner initially.

## 13. Webhook Delivery
Path: `services/webhook-delivery-service/`

Tenant subscriptions, signed delivery, retries, replay protection and delivery history.

## 14. Notifications
Path: `services/notification-service/`

Email/SMS/in-app notification orchestration, preferences and delivery state.

## 15. Reporting
Path: `services/reporting-service/`

Authorized reports over approved read models.

## 16. Audit
Path: `services/audit-service/`

Append-oriented security/business audit records, access controls and retention.

## 17. Document and Evidence
Path: `services/document-service/`

Private document metadata, access checks, MIME validation and malware-scan/quarantine states.

## 18. Integration Registry
Path: `services/integration-registry-service/`

Provider capabilities, environment references and integration health.

## 19. Compliance and Retention
Path: `services/compliance-service/`

Retention workflows, compliance evidence and policy enforcement.

## 20. Operations and Health
Path: `services/operations-service/`

Dependency status aggregation and administrative health views.

## Integration with Python streaming

The Python streaming repository owns provider callback ingestion and its operational delivery state initially. Java services consume versioned events and/or call authenticated internal APIs; they must not import Python modules or write into Python-owned tables.

## Transaction ownership

`transaction-service` is a proposed boundary only. Inspect `api.pesaguard` and designate exactly one canonical transaction owner before enabling persistence or production writes. Never dual-write competing authoritative records. The reconciliation service owns matching decisions and does not move funds or imply settlement.

## Cross-cutting requirements

OIDC/OAuth2 integration, deny-by-default authorization, tenant isolation, internal service identity, schema compatibility, durable publication, idempotent consumers, bounded retries, DLQ replay, database migrations, backup/restore testing, structured logs, metrics/traces, rate limits, dependency scanning, SBOM and documented operational runbooks.
