# Operational Readiness and Recovery

This project is a portfolio implementation. These procedures are instructions to generate evidence, not a claim that a recovery exercise has already passed.

## Readiness and observability

- `GET /health` reports process liveness.
- `GET /ready` verifies PostgreSQL connectivity and that the migrated outbox table is queryable. A 503 means the receiver should not receive traffic.
- `GET /metrics` exposes Prometheus metrics from the receiver process, including the pending/publishing/published outbox counts refreshed by readiness checks. Keep this endpoint on a trusted network or restrict it at the reverse proxy.
- Monitor outbox rows by status, age of the oldest pending row, relay retry count, consumer lag, dead-letter volume, PostgreSQL availability, and callback HTTP status/latency.
- Alert when the oldest pending outbox event exceeds the agreed service objective, when dead-letter volume rises, or when the relay/consumer is unhealthy. Alert delivery must be tested in the target environment.

## Shared rate limiting

For multi-worker or multi-instance deployments, configure REDIS_URL to a shared Redis service. The Compose stack configures the receiver to use its Redis service by default. If REDIS_URL is explicitly configured and Redis is unavailable, the receiver fails closed for rate-limited callback routes rather than silently downgrading to per-process limits. The in-process fallback is for local development only. Do not trust X-Forwarded-For unless trusted-proxy handling is correctly configured at the deployment boundary.

## Load testing

Use only synthetic payloads and a disposable environment.

```bash
python -m pip install -r requirements/base.txt -r requirements/data.txt -r requirements/load.txt
locust -f tests/load/locustfile.py --host=http://localhost:5000
```

Start with 1–5 users, confirm database and Kafka processing, then increase gradually. Capture the environment, commit SHA, user count, duration, request rate, error rate, p50/p95/p99 latency, outbox oldest-row age, consumer lag, and CPU/memory. Do not publish a capacity claim without the raw result file and reproducible command. Stop if the queue grows continuously or services become unhealthy.

## Backup

```bash
export POSTGRES_HOST=localhost POSTGRES_PORT=5433
export POSTGRES_DB=mpesa_analytics POSTGRES_USER=data_engineer
export POSTGRES_PASSWORD='your-local-only-password'
BACKUP_DIR=backups bash scripts/backup_postgres.sh
```

Store backups encrypted and access-controlled in real deployments; the local script creates a mode-600 dump and checksum but does not provide off-site storage or encryption at rest.

## Restore exercise

1. Create a new, isolated, empty disposable PostgreSQL database.
2. Set `RESTORE_TARGET_DATABASE_URL` to that database only.
3. Run the restore script with explicit confirmation.
4. Verify the checksum, schema, Alembic revision, critical row counts, outbox/dead-letter records, and application readiness.
5. Record duration and any data loss or errors. Never test restore against a production URL.

```bash
RESTORE_TARGET_DATABASE_URL='postgresql://user:pass@localhost:5433/mpesa_restore_test' \
CONFIRM_RESTORE=YES bash scripts/restore_postgres.sh backups/mpesa_YYYYMMDDTHHMMSSZ.dump
```

The restore script does not drop or clean target tables. Use an empty target database.

## Deployment verification

After migrations and services start, run:

```bash
BASE_URL=http://localhost:5000 bash scripts/verify_deployment.sh
# Optional end-to-end smoke (requires psql, DB access, relay and consumer running):
RUN_SYNTHETIC_SMOKE=1 BASE_URL=http://localhost:5000 POSTGRES_HOST=localhost POSTGRES_PORT=5433 POSTGRES_DB=mpesa_analytics POSTGRES_USER=data_engineer PGPASSWORD='your-local-only-password' bash scripts/verify_deployment.sh
```

Then verify that the outbox relay is running, submit one uniquely identified synthetic callback, confirm its outbox row reaches `published`, confirm the consumer writes the callback audit and (for C2B confirmation only) raw transaction row, and test that a malformed Kafka message is persisted to the dead-letter table before its offset advances.

## Release gate

A deployment is not considered verified until the readiness check, callback-to-Kafka-to-PostgreSQL test, DLQ test, backup/restore exercise, and a bounded load test all pass with recorded evidence. No production credentials or customer payloads belong in test artifacts.


## Release verification gate

Before proposing a release, complete this checklist with evidence tied to the exact commit SHA:

- [ ] Current-head quality-gates and security-scan workflows pass; review all scanner reports and CI artifacts.
- [ ] Fresh database migration and repeat migration pass; a sanitized supported legacy schema is tested separately.
- [ ] Duplicate transaction IDs cause an explicit migration failure without deleting records.
- [ ] Failure injection covers broker outage, relay retry and expired lease recovery, consumer DB failure, and DLQ-before-offset-commit.
- [ ] Multi-worker rate limiting is verified with shared Redis, including the configured-Redis-outage behavior.
- [ ] Synthetic callback round trip verifies outbox, Kafka, callback audit, and C2B raw transaction persistence.
- [ ] Backup checksum and restore pass against a separate empty disposable database; verify schema revision and critical row counts.
- [ ] Load evidence records commit, environment, user count, duration, throughput, p50/p95/p99 latency, error rate, outbox age, and consumer lag.
- [ ] Alert delivery is tested end-to-end; configuration files alone are not evidence of delivered alerts.
- [ ] Staging deployment, provider trust settings, rollback path, and production-data/secret exclusion are reviewed.

Record each item as passed, failed, or externally blocked. Do not mark production-ready until critical items have evidence. Provider-specific trust and staging/alert tests cannot be inferred from unit tests. Delivery remains at-least-once; downstream consumers must be idempotent.
