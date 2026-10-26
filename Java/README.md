# PesaGuard Java Services

Java 21 / Spring Boot workspace for PesaGuard's independently deployable business services. This is a structured scaffold, not a claim that every workflow is production-implemented.

## Build

Requires JDK 21 and Maven 3.9+.

```bash
cd Java
mvn -B -ntp verify
mvn -pl services/tenant-service -am verify
mvn -pl services/tenant-service spring-boot:run
```

Health endpoint: `/actuator/health`. Restrict management endpoints to trusted internal networks in production.

## Service catalog

- **API Gateway** — `services/api-gateway/`: Routing, request correlation and gateway policy; service-level authorization remains mandatory.
- **Identity Service** — `services/identity-service/`: OIDC/SSO, MFA integration and identity lifecycle; do not store plaintext passwords.
- **Tenant Service** — `services/tenant-service/`: Tenant lifecycle, tenant metadata and trusted tenant-context resolution.
- **Merchant Service** — `services/merchant-service/`: Merchant profiles and provider-account metadata, with secrets held separately.
- **Merchant Onboarding and KYB** — `services/onboarding-kyb-service/`: Verification cases, evidence workflow and real provider adapters with pending/manual-review states.
- **Team and Permissions** — `services/team-permissions-service/`: Membership, role assignment and tenant-scoped authorization policies.
- **Developer Portal** — `services/developer-portal-service/`: Developer projects, sandbox, API-key lifecycle, usage and production-access requests; store only secret hashes.
- **Payment Orchestration** — `services/payment-orchestration-service/`: Coordinates supported payment operations and state transitions; ingestion is not execution or settlement.
- **Canonical Transaction** — `services/transaction-service/`: Proposed canonical transaction owner; audit the existing backend before enabling writes.
- **Reconciliation** — `services/reconciliation-service/`: Ledger matching and persisted reconciliation decisions.
- **Risk and Fraud** — `services/risk-service/`: Risk signals and assessments; does not independently reverse payments or settle funds.
- **Callback Management** — `services/callback-management-service/`: Provider callback configuration and registration metadata; Python remains the ingestion owner initially.
- **Webhook Delivery** — `services/webhook-delivery-service/`: Tenant subscriptions, signed delivery, retries, replay protection and delivery history.
- **Notifications** — `services/notification-service/`: Email/SMS/in-app notification orchestration, preferences and delivery state.
- **Reporting** — `services/reporting-service/`: Authorized reports over approved read models.
- **Audit** — `services/audit-service/`: Append-oriented security/business audit records, access controls and retention.
- **Document and Evidence** — `services/document-service/`: Private document metadata, access checks, MIME validation and malware-scan/quarantine states.
- **Integration Registry** — `services/integration-registry-service/`: Provider capabilities, environment references and integration health.
- **Compliance and Retention** — `services/compliance-service/`: Retention workflows, compliance evidence and policy enforcement.
- **Operations and Health** — `services/operations-service/`: Dependency status aggregation and administrative health views.

## Enterprise rules

- Domain ownership must be explicit; no shared-table writes across services.
- Confirm the canonical transaction owner in the existing PesaGuard backend before enabling transaction-service writes.
- Reconciliation owns matching decisions; callback ingestion does not prove settlement.
- Use authenticated service-to-service APIs and versioned Kafka/Redpanda event contracts.
- Apply tenant-scoped authorization server-side, least-privilege database roles and secret-manager injection.
- State changes requiring events need a transactional outbox or proven equivalent; consumers must be idempotent and support bounded retries and durable DLQ replay.
- Use migrations, structured logs, trace/correlation IDs, metrics, SLOs, actionable alerts, resource limits, graceful shutdown, dependency scanning, SBOM and staging rollback tests.
- Do not commit secrets or real customer data.
- No production infrastructure or traffic is changed by this scaffold.

Each service README lists its implementation gates. A runnable health endpoint is not evidence that the domain service is production-ready.
