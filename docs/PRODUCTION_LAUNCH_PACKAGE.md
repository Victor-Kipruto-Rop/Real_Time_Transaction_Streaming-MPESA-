# Production Launch Package

This package is the operational handoff for the first production deployment and release approval.

## 1. Required GitHub production secrets

Add these as environment secrets under the GitHub `production` environment:

- `WEBHOOK_SIGNING_SECRET`
- `SECRET_KEY`
- `POSTGRES_PASSWORD`
- `DARAJA_CONSUMER_KEY`
- `DARAJA_CONSUMER_SECRET`
- `DARAJA_PASSKEY`
- `AWS_ROLE_TO_ASSUME` or `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY`
- `SLACK_WEBHOOK_URL`
- `PAGERDUTY_API_KEY`

Required production-only values must be non-empty and not match placeholder/default patterns such as `set_me_via_env`, `change_me`, `admin123`, `placeholder`, `example`, or `default`.

## 2. Required GitHub production variables

Add these as environment variables or repository variables, depending on your GitHub setup:

- `PROD_BASE_URL`
- `PROD_NAMESPACE`
- `AWS_REGION`
- `KAFKA_BROKERS`
- `POSTGRES_HOST`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PORT`

Example values:

- `PROD_BASE_URL=https://api.your-domain.com`
- `PROD_NAMESPACE=mpesa-production`
- `AWS_REGION=us-east-1`
- `KAFKA_BROKERS=kafka-broker-1:9092,kafka-broker-2:9092`

## 3. Required environment protection rules

- Enable GitHub environment protection for `production`
- Require manual approval before the deployment job can proceed
- Require at least one reviewer or on-call owner
- Block deployment if required secrets or variables are missing or default-looking

## 4. Production launch checklist

- [ ] Required GitHub environment secrets are configured and populated
- [ ] Required GitHub environment variables are configured and valid
- [ ] No repo-tracked secrets remain in source files or config files
- [ ] Runtime config validation is green
- [ ] PostgreSQL health check is green
- [ ] Kafka broker health check is green
- [ ] Producer → Kafka → consumer → Postgres roundtrip passes
- [ ] Replay protection and duplicate idempotency checks pass
- [ ] Deploy workflow is configured for `production` environment with manual approval
- [ ] Rollback target and previous working image are documented
- [ ] Smoke tests pass against the production target
- [ ] Health gate and rollback path are ready before launch

## 5. Launch decision rule

Proceed to production only when all required secrets are valid, runtime proof is attached to the release, the health gate is green, and the production environment has received explicit approval.

If any gate fails, deployment remains in safe hold.
