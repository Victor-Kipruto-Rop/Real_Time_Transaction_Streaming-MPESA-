# Operational Readiness and Recovery

This project is a portfolio implementation. These procedures are instructions to generate evidence, not a claim that a recovery exercise has already passed.

## Readiness and observability

- `GET /health` reports process liveness.
- `GET /ready` verifies PostgreSQL connectivity and that the migrated outbox table is queryable. A 503 means the receiver should not receive traffic.
- `GET /metrics` exposes Prometheus metrics from the receiver process. Keep this endpoint on a trusted network or restrict it at the reverse proxy.
- Monitor outbox rows by status, age of the oldest pending row, relay retry count, consumer lag, dead-letter volume, PostgreSQL availability, and callback HTTP status/latency.
- Alert when the oldest pending outbox event exceeds the agreed service objective, when dead-letter volume rises, or when the relay/consumer is unhealthy. Alert delivery must be tested in the target environment.

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
```

Then verify that the outbox relay is running, submit one uniquely identified synthetic callback, confirm its outbox row reaches `published`, confirm the consumer writes the callback audit and (for C2B) raw transaction row, and test that a malformed Kafka message is persisted to the dead-letter table before its offset advances.

## Release gate

A deployment is not considered verified until the readiness check, callback-to-Kafka-to-PostgreSQL test, DLQ test, backup/restore exercise, and a bounded load test all pass with recorded evidence. No production credentials or customer payloads belong in test artifacts.
