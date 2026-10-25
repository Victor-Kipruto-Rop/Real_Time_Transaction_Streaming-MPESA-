# Component Inventory

**Status:** Initial inventory from inspected repository files; verify against the full tree before release.

| Area | Evidence / location | Current understanding | Verification still required |
|---|---|---|---|
| Webhook ingress | `ingestion/webhook_receiver.py`, `Dockerfile.webhook` | Flask receiver for C2B, B2C and STK callback routes | Enumerate every route; validate request limits, schemas, trust controls and response semantics |
| Application configuration | `app/config.py`, `.env.example` | Environment-backed settings with Pydantic validators | Validate all environment variables, defaults, production fail-fast behavior and secret handling |
| Persistence | `app/database/connection.py`, `app/database/idempotency.py` | SQLAlchemy-backed database helpers and durable idempotency records | Inspect models, constraints, migrations, transaction boundaries and recovery |
| Event streaming | Compose Kafka service and repository README | Kafka is part of the intended architecture | Trace actual producer/consumer implementations, delivery guarantees, retry/DLQ behavior and offset commits |
| Replay controls | `ingestion/webhook_receiver.py` | Redis check plus process-local fallback; database idempotency helper | Prove concurrency safety, cross-instance behavior, TTL policy and fail-closed/fail-open policy |
| Analytics | `dbt/` and Compose dbt service | dbt is part of the declared analytics workflow | Verify model lineage, tests, source freshness, reproducibility and whether reconciliation uses a separate source of truth |
| Observability | `grafana/`, `monitoring/`, webhook metrics imports | Grafana/metrics assets are present in the described architecture | Confirm scrape targets, actionable alerts, redaction, dashboards and alert delivery |
| Container/runtime | `Dockerfile`, `Dockerfile.webhook`, Compose file | Multiple container definitions exist | Select canonical images, align ports/health checks/dependencies and run image builds |
| Developer commands | `Makefile` | Setup, infrastructure, tests, analytics and operational targets are declared | Run each documented target in a clean environment; remove stale or misleading commands |
| Tests | Repository test paths referenced by Makefile/README | Test commands are advertised | Enumerate tests, run them, identify skipped/flaky tests and add integration/concurrency coverage |
| CI | `.github/workflows/` | Workflow inventory not yet confirmed by this initial audit | Enumerate existing workflows and ensure required checks run on PRs |
| Secrets and credentials | `.env.example`, settings, Compose environment | Secrets are intended to come from environment | Scan history and repository; verify no secrets in logs, fixtures, screenshots or artifacts |

## Canonical runtime contract (to be decided after verification)

Do not assume the README, a Dockerfile, or a Compose service is authoritative without testing. The release contract should explicitly state:

- supported Python version;
- canonical webhook entry point and bind port;
- required environment variables and their validation rules;
- database migration/startup procedure;
- Kafka topic names and consumer group behavior;
- required versus optional dependencies;
- local development command and production container command;
- health/readiness endpoints and their dependency semantics.
