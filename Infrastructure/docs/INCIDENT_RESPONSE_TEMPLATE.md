# Incident Response Template

Use this as the standard response format when a production issue or degraded service condition is detected.

## 1. Incident metadata

- Incident ID:
- Date/time started:
- Reported by:
- Affected service(s):
- Severity:
- Status:

## 2. Summary

Provide a brief summary of the issue, the impact, and the current state:

- What failed or degraded?
- Which customers or endpoints are affected?
- What is the user-visible impact?
- What is the current business impact?

## 3. Detection and ownership

- Detection method:
- Owner on call:
- Engineering lead:
- Incident commander:
- Communication channel:

## 4. Scope and impact

- Affected systems: webhook receiver, Kafka consumer, DB, alerting, analytics
- Partial or full outage:
- Error rate or alert level:
- Transaction loss or replay risk:
- Data integrity risk:

## 5. Immediate containment

- [ ] Isolate the service, namespace, or ingress
- [ ] Pause deployment or traffic if necessary
- [ ] Reduce or disable affected consumers if safe
- [ ] Capture logs and metrics snapshots
- [ ] Enable fail-safe mode if applicable

## 6. Investigation and diagnosis

- Likely root cause:
- Evidence collected:
- Relevant logs:
- Relevant alert IDs or dashboards:
- Related deployment tag or commit:

## 7. Recovery actions

- [ ] Restore the last known-good image or config
- [ ] Re-run smoke tests or health checks
- [ ] Confirm database and Kafka are healthy
- [ ] Verify replay protection and idempotency are active
- [ ] Confirm alerting returns to normal

## 8. Communication plan

- Initial notification sent at:
- Status updates scheduled for:
- Internal stakeholders notified:
- Customer-facing communication required:

## 9. Resolution criteria

The incident is resolved only when:

- health checks are green,
- smoke tests pass,
- duplicate or replay issues are absent,
- no critical alerts remain active,
- and the incident owner confirms service recovery.

## 10. Post-incident follow-up

- [ ] Root cause documented
- [ ] Fix or mitigation tracked in project backlog
- [ ] Runbook updated
- [ ] Postmortem scheduled
- [ ] Lessons learned recorded
