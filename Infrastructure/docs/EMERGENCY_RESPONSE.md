# Emergency Response / Incident Flow

## Purpose

This one-page flow defines how the production team responds to outages, failed webhooks, Kafka backlog, or duplicate transaction issues.

## Production approval gate

Before any release is promoted:

1. Open GitHub repository settings.
2. Navigate to Environments and select the production environment.
3. Require manual approval for deployment jobs.
4. Add at least one reviewer or designated on-call approver.
5. Confirm the production environment uses a short list of required secrets:
   - `WEBHOOK_SIGNING_SECRET`
   - `SECRET_KEY`
   - `POSTGRES_PASSWORD`
   - `AWS_ROLE_TO_ASSUME` or AWS key pair
   - `PROD_BASE_URL`

If any required secret is missing or default-looking, the workflow must fail closed.

## Incident triage flow

1. Detect the issue
   - health checks fail
   - webhook error rate spikes
   - duplicate transactions appear
   - Kafka lag exceeds threshold
   - database or redis becomes unhealthy

2. Declare severity
   - Severity 1: total platform outage or data loss risk
   - Severity 2: degraded service or webhook failure affecting live flows
   - Severity 3: non-critical warnings or minor performance drift

3. Assign ownership
   - Primary owner: on-call engineer
   - Secondary owner: platform lead
   - Incident comms channel: internal alerts and status channel

4. Contain the issue
   - pause or disable rollouts
   - freeze new production deployments
   - confirm whether the issue is in ingestion, Kafka, database, or deployment state
   - keep the last known-good image tag available

5. Validate the root cause
   - confirm signature verification state
   - check DB idempotency records and replay guard
   - inspect Kafka lag, DLQ volume, and consumer logs
   - verify recent deployment or config drift

6. Recover
   - restore the last green deployment image
   - revert config or secrets if drift caused the issue
   - confirm pods are ready and ingress is serving healthy responses

7. Verify recovery
   - run health checks
   - run the production smoke suite
   - verify transaction continuity and duplicate prevention
   - observe for a short stability window before closing the incident

## Communication template

Status update format:

- Incident: [brief name]
- Severity: [1/2/3]
- Status: Investigating / Contained / Recovering / Resolved
- Impact: [customers, throughput, payment flow]
- Owner: [name]
- ETA: [next update time]

## Closure criteria

An incident is considered resolved only when all of the following are true:

- service health is green
- no critical alert is firing
- rollback or recovery action is confirmed in logs
- smoke tests pass
- data integrity checks confirm no duplicates or losses
- the incident is documented with lessons learned
