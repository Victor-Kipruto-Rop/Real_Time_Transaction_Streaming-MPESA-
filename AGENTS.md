# Project Agent Instructions

This project is the M-Pesa real-time transaction streaming pipeline in the DATA_ENGINEERING suite.

## Scope

- Keep the pipeline runnable end to end: Daraja/webhook ingestion, Kafka streaming, Postgres storage, dbt transforms, analytics, tests, and local Docker dependencies.
- Do not treat this as a generic web SaaS app. The production goal is a secure, observable fintech data pipeline.

## Local Commands

- `make setup` installs Python dependencies into `.venv`.
- `make infra-up` starts Postgres, Kafka, Redis, webhook receiver, and consumer services.
- `make verify` runs the local component verification script.
- `make test-all` runs the Python test suite.
- `make transform` runs dbt models and tests against Postgres.

## Engineering Rules

- Never commit real Daraja, cloud, database, or messaging credentials.
- Keep `.env` local and update `.env.example` for configuration templates.
- Prefer deterministic local tests and fixtures when live Daraja or cloud access is unavailable.
- Keep container-internal service URLs separate from host URLs: containers should use `postgres:5432` and `kafka:29092`; host tools should use `localhost` with the configured published ports.
- Use structured errors and sanitized logs; do not log secrets, auth headers, full M-Pesa callback payloads, or customer PII unnecessarily.
- Add tests for parsing, validation, permissions/security checks, and integration contracts when changing those paths.

## Verification Before Handoff

Run the most relevant checks for the files changed. For broad pipeline changes, prefer:

```bash
make verify
make test-all
make transform
```

If Docker or local network access is blocked by the execution environment, verify with the available local tests and document the skipped live dependency clearly.
