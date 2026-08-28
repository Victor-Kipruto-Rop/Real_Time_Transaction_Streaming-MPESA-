# Production Runbook

## 1. Entry criteria

Only deploy to production when all of the following are true:

- The version tag matches the semantic version contract, for example `v1.2.3`.
- The staging deployment passed the required smoke gates and the production secret policy checks.
- All required secrets are populated in the GitHub environment or secret manager.
- The production base URL and namespace are configured.
- The database snapshot or backup is available for rollback.

## 2. Required environment values

Set these as GitHub environment secrets or repository variables before production rollout:

- `WEBHOOK_SIGNING_SECRET`
- `SECRET_KEY`
- `POSTGRES_PASSWORD`
- `AWS_ROLE_TO_ASSUME` or `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- `PROD_BASE_URL`

Do not commit plaintext values to the repo. The repo currently uses env-safe placeholders and the workflow requires non-default values.

## 3. Deployment sequence

1. Confirm the target version is approved.
2. Trigger the production workflow manually or by pushing a release tag.
3. Wait for `validate` to complete successfully.
4. Ensure the security scan passes.
5. Confirm the build and push job completes for all production images.
6. Capture a fresh database snapshot before the rollout.
7. Apply the production deployment using Kubernetes rollout checks.
8. Run smoke tests against the live production deployment.
9. Verify ingress, pod health, and Kafka consumer health.
10. Confirm alerts are quiet for a fixed observation window.

## 4. Post-deploy validation

Use the following checks after deployment:

```bash
kubectl get pods -n mpesa-production
kubectl get deployments -n mpesa-production
kubectl logs deploy/webhook-receiver -n mpesa-production --tail=100
kubectl logs deploy/kafka-consumer -n mpesa-production --tail=100
curl -f https://api.your-domain.com/health
pytest tests/e2e/smoke_tests.py -q --maxfail=1
```

Validate at least these business outcomes:

- webhook signature verification remains enabled
- replay protection prevents duplicate events
- Kafka consumer retry and DLQ paths function
- idempotency state is persisted in the database
- no spike in failed or dead-letter messages

## 5. Incident and rollback triggers

Rollback immediately if any of the following occurs:

- health checks fail repeatedly
- webhook verification fails for valid requests
- duplicate transactions are accepted
- consumer lag or DLQ volume reaches an alert threshold
- production smoke tests fail after promotion

## 6. Normal rollback procedure

1. Stop the rollout if the workflow is still running.
2. Revert to the previous stable image tag in Kubernetes.
3. Restore the last known-good deployment state from the backup manifest.
4. Restart affected workloads and wait for readiness.
5. Run the smoke suite again.
6. Re-enable traffic only after validation succeeds.

Example rollback commands:

```bash
kubectl set image deployment/webhook-receiver \
  webhook-receiver=ghcr.io/<org>/<repo>-webhook-receiver:<last-good-tag> \
  -n mpesa-production

kubectl set image deployment/kafka-consumer \
  kafka-consumer=ghcr.io/<org>/<repo>-kafka-consumer:<last-good-tag> \
  -n mpesa-production

kubectl rollout status deployment/webhook-receiver -n mpesa-production --timeout=10m
kubectl rollout status deployment/kafka-consumer -n mpesa-production --timeout=10m
```

## 7. Operational guardrails

- Never deploy without a signed, reviewed release tag.
- Never keep credentials in the repo, backup archives, or templates.
- Never merge a production deployment if the required environment variables are missing.
- Keep a recovery image tag and snapshot for at least the current release window.
- Record the cause, fix, and validation outcome for every rollback event.
