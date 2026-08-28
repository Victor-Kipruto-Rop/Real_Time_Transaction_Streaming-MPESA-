# Production Approval Checklist

Use this checklist before approving the production deployment or any major release.

## 1. Release ownership

- [ ] A release owner is named and confirmed.
- [ ] A production on-call or incident owner is assigned.
- [ ] The release version is reviewed and tagged as the intended production target.
- [ ] The previous stable version and rollback target are recorded.
- [ ] A deployment or release note is prepared for the team.

## 2. Runtime proof and validation

- [ ] The runtime proof artifact is attached to the deployment run.
- [ ] PostgreSQL health check is green.
- [ ] Kafka broker health check is green.
- [ ] The producer → Kafka → consumer → Postgres roundtrip passes.
- [ ] Replay protection is green against duplicate payloads.
- [ ] Idempotency enforcement is green and duplicate writes remain blocked.
- [ ] Smoke tests pass in the target environment.
- [ ] Alerts and error budgets are reviewed before approval.

## 3. Security and environment controls

- [ ] All required production secrets are populated and non-default.
- [ ] There are no repo-stored secrets or plaintext credentials in tracked files.
- [ ] `WEBHOOK_SIGNING_SECRET` is set and valid.
- [ ] `SECRET_KEY` is set and valid.
- [ ] `POSTGRES_PASSWORD` is set and valid.
- [ ] `PROD_BASE_URL` is configured and matches the load balancer / ingress target.
- [ ] `AWS_ROLE_TO_ASSUME` or the AWS access key pair is configured.
- [ ] The workflow environment is set to `production` and requires approval.

## 4. Deployment gates

- [ ] The `production` GitHub environment has required reviewers configured.
- [ ] The workflow is triggered manually via `workflow_dispatch` or a signed release tag.
- [ ] The workflow is not skipped on required validation steps.
- [ ] Security scans are green.
- [ ] Build and image push jobs complete successfully.
- [ ] Database snapshot or backup is captured before rollout.
- [ ] Rollback state and last known-good image are available.

## 5. Pre-launch signoff

Before approving the production release, confirm the following:

- [ ] The release is not blocked by failed gates.
- [ ] Post-deploy health checks are planned and ready to run.
- [ ] Incident escalation contact information is confirmed.
- [ ] The rollback procedure is reviewed and ready.
- [ ] The business owner and tech owner both approve the launch.

## 6. Production environment secret and variable set

Required GitHub environment secrets:

- `WEBHOOK_SIGNING_SECRET`
- `SECRET_KEY`
- `POSTGRES_PASSWORD`
- `AWS_ROLE_TO_ASSUME` or `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- `DARAJA_CONSUMER_KEY`
- `DARAJA_CONSUMER_SECRET`
- `DARAJA_PASSKEY`
- `SLACK_WEBHOOK_URL`
- `PAGERDUTY_API_KEY`

Required GitHub repository or environment variables:

- `PROD_BASE_URL`
- `PROD_NAMESPACE`
- `AWS_REGION`
- `KAFKA_BROKERS`
- `POSTGRES_HOST`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PORT`

Release approval rule:

- If any required secret is missing, defaulted, or placeholder-like, the deployment must stop and remain in hold state until fixed.
