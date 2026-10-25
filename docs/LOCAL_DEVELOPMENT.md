# Local Development and Startup

## Prerequisites

- Git
- Docker Engine and Docker Compose v2
- Python 3.11 for the focused configuration tests; use the version declared by the canonical runtime once Phase 2 confirms it

## Configure secrets before starting

```bash
cp .env.example .env
```

Edit `.env` and set strong, unique local-only values for at least:

- `POSTGRES_PASSWORD`
- `GRAFANA_ADMIN_PASSWORD`
- `UI_TOKEN` (needed for the browser webhook demo)

Keep `.env` untracked. Never paste production Daraja keys, passkeys, customer data, or production database credentials into a local demo. Use sandbox credentials only when the feature requires provider access.

## Validate and start

```bash
docker compose -f docker-compose.yml config --quiet
make infra-up
docker compose ps
docker compose logs --tail=100 postgres webhook-receiver kafka
```

The Compose file deliberately fails fast when the database or Grafana admin password is missing. Do not weaken this behavior by committing default passwords. Compose runs the versioned Alembic migration service before the webhook, relay, and consumer start.

When running an application entry point directly rather than through Compose, apply the schema first:

```bash
alembic upgrade head
```

Application imports and consumer constructors must not create or mutate the schema. If a migration fails, stop and reconcile the database state; do not fall back to `init_db()` as an automatic repair mechanism.

Check the receiver's health endpoint:

```bash
curl --fail --silent --show-error http://localhost:5000/health
```

A successful HTTP health response alone does not prove that Kafka delivery, transaction persistence, provider authentication, or reconciliation works. Verify those paths separately.

## Run focused configuration tests

```bash
python -m pip install "pydantic==2.5.0" "pydantic-settings==2.1.0" "python-dotenv==1.0.0" "pytest==8.3.5"
python -m pytest -q tests/test_config_security.py
```

## Browser demo caution

The webhook sender UI supports a query-string token to make the browser demo usable. Use it only on localhost or a sandbox environment; URLs may be retained by browser history or intermediary logs. Do not enable the demo UI on a public production endpoint. The UI is disabled if `UI_TOKEN` is unset.

## Stop services

```bash
make infra-down
```

Do not use destructive volume-removal flags unless you intentionally want to delete local PostgreSQL/Grafana data.
