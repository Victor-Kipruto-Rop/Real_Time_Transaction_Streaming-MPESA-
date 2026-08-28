# Rollback Checklist

Use this checklist any time a production release must be reverted or paused.

## Immediate actions

- [ ] Confirm the incident severity and scope.
- [ ] Stop further production traffic or disable the rollout.
- [ ] Record the current version, failing checks, and time of incident.
- [ ] Ensure the engineering lead or on-call owner approves the rollback.

## Snapshot and safety checks

- [ ] Confirm the production database snapshot exists.
- [ ] Confirm the last known-good deployment image tag is available.
- [ ] Confirm the Kubernetes namespace and service names are correct.
- [ ] Confirm ingress, secrets, and env vars remain valid.

## Restore previous deployment

- [ ] Revert the webhook service image to the previous stable version.
- [ ] Revert the Kafka consumer image to the previous stable version.
- [ ] Restore any configuration manifests from the backup snapshot.
- [ ] Wait for the rollout to finish and pods to become ready.

## Validation after rollback

- [ ] Run health checks for the application and Kafka consumer.
- [ ] Run the production smoke tests.
- [ ] Check completed transactions and failed message counts.
- [ ] Verify webhook replay protection is still working.
- [ ] Verify no duplicate transaction writes were introduced.

## Documentation and follow-up

- [ ] Capture the root cause and decision reason for rollback.
- [ ] Open or link the incident issue.
- [ ] Update the runbook with any lessons learned.
- [ ] Schedule a postmortem or recovery review.

## Escalation notes

If rollback does not restore service health quickly, escalate to the infrastructure owner and disable automated traffic routing before making repeated changes.
