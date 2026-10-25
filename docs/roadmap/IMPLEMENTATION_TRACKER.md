# Implementation Tracker

**Goal:** Build a reliable, reproducible portfolio-grade M-Pesa event streaming project.  
**Rule:** Phase completion requires evidence, not just changed files.

| Phase | Scope | Status | Gate to close |
|---|---|---|---|
| 0 | Repository audit and baseline | In progress | Initial audit, inventory, issue register and baseline-status docs added; full tree/runtime verification pending |
| 1 | Configuration, installation and startup reliability | In progress | PostgreSQL healthcheck quoting fixed; Compose requires explicit DB/Grafana passwords; local setup guide and container healthchecks added; CI Compose validation still unconfirmed |
| 2 | Architecture and code quality | Not started | Canonical entry points, module boundaries, supported Python version and dependency contract |
| 3 | Webhook security and input validation | In progress | Trust model documented; request body bounded; forwarded IP spoofing reduced; UI disabled without token; B2C/STK validators and configured signature checks added; provider trust and live tests remain |
| 4 | Idempotency and data integrity | In progress | Added callback-scoped event identities so C2B validation and confirmation do not collide; durable PostgreSQL outbox, stable callback event key and relay added; concurrent PostgreSQL and broker-failure tests pending |
| 5 | Kafka reliability and recovery | In progress | Consumer offset auto-commit disabled; manual commits occur after handled persistence/duplicates; PostgreSQL dead-letter persistence before offset commit added; live broker/DLQ tests wired in CI, run result pending |
| 6 | PostgreSQL persistence, migrations and recovery | In progress | Raw table DDL now supports PostgreSQL and SQLite and includes consumer-required columns; Alembic baseline and Compose migration gate added; fresh/existing database migration and backup/restore evidence pending |
| 7 | Data quality, reconciliation and dbt analytics | Not started | Tested lineage and models; reconciliation source of truth documented |
| 8 | Automated testing and CI | In progress | Added unit/contract checks plus disposable PostgreSQL/Kafka integration job; latest run must pass before merge |
| 9 | Observability and operational monitoring | In progress | Receiver Prometheus endpoint includes outbox status and oldest-pending age; alert rule added; alert delivery and end-to-end scrape still require verification |
| 10 | Load testing and performance engineering | In progress | Synthetic Locust profile and a bounded CI load-smoke step added; performance results and capacity claims must wait for a passing run and artifact review |
| 11 | Deployment, security audit and disaster recovery | In progress | Deployment readiness script, guarded backup/restore scripts and a disposable CI restore exercise added; staging, security findings and restore evidence remain pending |
| 12 | Portfolio documentation and release | In progress | README, trust model and operational runbook updated; release remains blocked until CI and deployment evidence are reviewed |

## Execution order

- Complete Phases 0–2 before broad refactoring.
- Implement Phases 3–6 before claiming reliable financial event processing.
- Phase 7 depends on validated persistence and a defined independent reconciliation source.
- Phase 8 runs throughout, with gates tightened as the system matures.
- Phase 10 may collect an early baseline, but performance claims wait until correctness and instrumentation are verified.
- Phase 11 is staging-only until explicitly reviewed; no production resources or real customer data are to be changed as part of this repository task.
- Phase 12 comes last and reports only proven capabilities.

## New delivery path

1. Webhook validates callback shape and configured custom HMAC policy.
2. PostgreSQL `event_outbox` inserts one row under a stable callback-scoped key; the HTTP handler only acknowledges after commit.
3. `outbox-relay` publishes pending rows and marks them published only after the Kafka delivery callback confirms success. Failed sends return to pending with exponential backoff and a lease permits recovery after relay restarts.
4. Consumer writes every accepted callback to `mpesa_callback_events`; only C2B confirmations upsert `mpesa_transactions_raw` because validation is not proof of payment.
5. Invalid Kafka messages are written to `kafka_dead_letters` before their offsets are committed. If DLQ persistence fails, the offset is retained.

Delivery is at-least-once, not exactly-once. A process crash after broker delivery but before marking the outbox row published may produce a duplicate, which is why event identity and consumer idempotency remain required.

## Current change boundary

Work is being prepared on `hardening/portfolio-10-of-10` and the existing draft pull request. `main` is not being modified directly. The PostgreSQL Compose healthcheck quoting has been corrected. A previous workflow run for an earlier head failed; its logs were not available through the connected GitHub interface. The newest head must pass CI before any runtime capability is marked verified.
