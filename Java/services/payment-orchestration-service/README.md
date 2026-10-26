# Payment Orchestration

**Responsibility:** Coordinates supported payment operations and state transitions; ingestion is not execution or settlement.

## Scaffold currently provides
- Java 21 / Spring Boot application entry point.
- Actuator health and readiness/liveness probes.
- Validation, Spring Security, OAuth2 resource-server and Prometheus dependencies.
- Graceful shutdown configuration.

## Required before production
1. Define OpenAPI and event contracts with an accountable owner.
2. Implement domain endpoints and validation; no business workflow is implemented by this scaffold.
3. Configure OIDC issuer, audience and JWT validation; ensure endpoints are not accidentally public.
4. Implement tenant-scoped authorization and service-to-service identity.
5. Define persistence ownership and migrations if needed; use least-privilege database roles.
6. Implement outbox/idempotency/retry/DLQ where applicable.
7. Add unit, integration, contract, security and recovery tests.
8. Add structured logs, traces, SLOs, alerts, rate limits and runbooks.
9. Test secrets/configuration and failure recovery in staging.
10. Confirm no competing authoritative data store is created.

Run from `Java/`: `mvn -pl services/payment-orchestration-service -am spring-boot:run`. Default local port: 8088. Health: `/actuator/health`.
