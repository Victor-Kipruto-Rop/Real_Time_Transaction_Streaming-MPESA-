# Production Go-Live Checklist

Use this checklist before the first production deployment or any major release. This is the final signoff gate for service readiness, environment correctness, and operational safety.

## 1. Release approval and ownership

- [ ] A named release owner has been assigned.
- [ ] A named on-call or incident owner has been assigned.
- [ ] The production environment in GitHub has required manual approval enabled.
- [ ] At least one reviewer or approver is configured for the production environment.
- [ ] The release tag or version is identified and reviewed.
- [ ] The rollback target and last known-good image are documented.

## 2. Environment and secret validation

- [ ] Required GitHub/environment secrets are populated for production.
- [ ] No repo-stored secret, password, token, or credential remains in source files or backup archives.
- [ ] The following values are present and non-default:
  - [ ] `WEBHOOK_SIGNING_SECRET`
  - [ ] `SECRET_KEY`
  - [ ] `POSTGRES_PASSWORD`
  - [ ] `AWS_ROLE_TO_ASSUME` or AWS credentials
  - [ ] `PROD_BASE_URL`
- [ ] Environment names and namespaces are consistent across manifests, scripts, and deployment workflows.
- [ ] Production config values do not contain placeholder values such as `change_me`, `admin123`, or equivalent defaults.

## 3. Runtime correctness and security

- [ ] Webhook signature verification is enabled and tested against a signed callback.
- [ ] Replay detection is active and verified against a duplicate payload.
- [ ] Duplicate transaction protection is enforced at the ingress and persistence layers.
- [ ] Database-backed idempotency is enabled and validated in the target environment.
- [ ] Kafka producer/consumer retry flow is configured and proven in a live roundtrip.
- [ ] DLQ handling is configured and monitored.
- [ ] Consumer failure states are recorded and visible in logs.
- [ ] Health checks for Kafka, database, webhook endpoint, and data freshness are configured.
- [ ] Alerting thresholds are reviewed for production traffic patterns.
- [ ] The runtime proof is attached to the release record:
  - [ ] Postgres health check passes
  - [ ] Kafka broker API check passes
  - [ ] Producer → Kafka → consumer → Postgres roundtrip succeeds
  - [ ] Duplicate idempotency detection is green
  - [ ] Replay guard rejects repeat payloads without writes

## 4. Deployment and infrastructure validation

- [ ] Target namespace matches the production deployment intent.
- [ ] Ingress, service, and pod names match the deployed environment.
- [ ] Kubernetes manifests are applied to the intended cluster and not a dev/staging target.
- [ ] Secrets and config maps are mounted correctly.
- [ ] Storage, DB, and networking requirements are verified.
- [ ] Monitoring and log pipelines are connected to the production target.
- [ ] Grafana dashboard pack is available and connected to the correct datasource.
- [ ] The workflow is pinned to an explicit production environment with manual approval gating enabled in GitHub.
- [ ] Production deployment is blocked when required secrets or vars are missing or still default-valued.

## 5. Release pre-flight checks

- [ ] Unit tests pass for config and idempotency behavior.
- [ ] Smoke tests pass in the target environment.
- [ ] Production workflow validation is green.
- [ ] Security checks and environment validation are green.
- [ ] Database snapshot or backup is captured before rollout.
- [ ] Last known-good deployment artifact is preserved and accessible.
- [ ] Rollback steps are rehearsed and documented.

## 6. Live production verification

After deployment, confirm all of the following before declaring launch complete:

- [ ] Health checks return green for application, database, and Kafka.
- [ ] Webhook endpoint responds successfully and without signature failures.
- [ ] Transaction throughput is stable and within expected limits.
- [ ] No duplicate transaction writes are observed.
- [ ] Kafka lag remains within threshold.
- [ ] Data freshness remains within the defined SLO window.
- [ ] No critical alerts are firing after the first observation period.
- [ ] Error rate remains within the accepted budget.
- [ ] Guardrails for replay protection remain active.

## 7. Incident readiness

- [ ] On-call escalation path is documented and active.
- [ ] Incident response flow is available to the team.
- [ ] Rollback checklist is available and current.
- [ ] Runbook is reviewed and matches the active environment.
- [ ] Communication channel and ownership routing are clear.
- [ ] Recovery image tag and config backup are ready for immediate use.

## 8. Final signoff

Only sign off when all items above are complete and evidence is collected.

- [ ] Release owner signs off.
- [ ] Incident owner confirms readiness.
- [ ] Production environment approval is recorded.
- [ ] Smoke and health checks are attached to release evidence.
- [ ] Rollback is confirmed as ready.
- [ ] Production launch proceeds with explicit approval and monitoring.

## 9. Launch decision rule

The system may proceed to production only when:

- all required secrets are valid and non-default,
- runtime protections are proven,
- monitoring and rollback are active,
- the target environment matches production intent,
- and the release owner has approved the launch.

If any gate fails, the release must stop and remain in safe hold until resolved.
