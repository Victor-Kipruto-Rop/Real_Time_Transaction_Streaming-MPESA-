# Release Checklist

Use this checklist for every production release and hotfix.

## 1. Release readiness

- [ ] Version tag matches the agreed release contract and is unique.
- [ ] Change summary, rollback plan, and owner are documented.
- [ ] The deployment branch or tag is reviewed and approved.
- [ ] The production environment is configured with required secrets and variables.
- [ ] The last known-good image tag is available for immediate rollback.
- [ ] A fresh database snapshot or backup exists before deployment.
- [ ] No default or placeholder secrets remain in the repo, manifests, or templates.

## 2. Quality gates

- [ ] Unit tests pass.
- [ ] Smoke tests pass against the target environment.
- [ ] Webhook signature validation is enabled.
- [ ] Replay protection is active and idempotency persists in the database.
- [ ] Kafka retry and DLQ handling were tested under failure conditions.
- [ ] Health checks and alert thresholds are validated.
- [ ] Security scans and config validation are green.

## 3. Production pre-deploy checks

- [ ] Confirm namespace, ingress, and service names are correct for the target environment.
- [ ] Verify there is no environment drift between staging and production.
- [ ] Confirm the secrets manager or GitHub environment includes the required values.
- [ ] Validate the deployment workflow has the required approval gate enabled.
- [ ] Ensure monitoring dashboards and alert routes are active and mapped correctly.

## 4. Deployment execution

- [ ] Trigger the release from the approved branch or tag.
- [ ] Wait for the validation stages to finish without warnings or blocked steps.
- [ ] Confirm the build, push, and rollout jobs all succeed.
- [ ] Watch pod readiness, ingress health, and consumer health during the first observation window.
- [ ] Confirm webhook success rate and transaction throughput remain within target bounds.

## 5. Post-deploy verification

- [ ] Application health is green.
- [ ] Kafka lag is within the agreed threshold.
- [ ] Database freshness is within the SLO window.
- [ ] Duplicate transactions are not being accepted.
- [ ] No critical alerts remain firing.
- [ ] The primary dashboard pack reflects normal operating conditions.

## 6. Release sign-off

Release is approved only when all gates are green and the on-call owner confirms:

- service health is stable,
- no data integrity issues are detected,
- no rollback decision is required,
- and monitoring remains healthy for the required observation window.

## 7. Release closure

- [ ] Capture release summary, metrics, and evidence.
- [ ] Link the deployment record to the incident tracker or PR.
- [ ] Record follow-up items and any post-release watch points.
- [ ] Archive the last known-good image tag and backup state.
