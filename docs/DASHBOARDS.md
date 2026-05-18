# M-Pesa Dashboard Runbook

This project ships provisioned Grafana dashboards for the real-time M-Pesa
streaming pipeline. Dashboards read from Postgres and the dbt models in
`public_staging` and `public_marts`.

## Dashboard Set

- **M-Pesa Executive Command Center**: value, volume, active customers, average ticket, amount mix, and top account references.
- **M-Pesa Live Operations**: ingestion rate, pipeline freshness, duplicate IDs, current throughput, and latest confirmations.
- **M-Pesa Fraud and Risk Monitoring**: high-value events, night transactions, velocity signals, and customers requiring review.
- **M-Pesa Customer and Merchant Intelligence**: repeat usage, customer value bands, timing patterns, and top customers.
- **M-Pesa Data Quality and Reliability**: missing fields, invalid amounts, raw-to-staged counts, model freshness, and duplicates.

## Local Startup

```bash
make transform
make dashboards
make grafana-up
```

Grafana runs at `http://localhost:3000`.

Default local credentials:

```text
username: admin
password: admin123
```

Override them with `GRAFANA_ADMIN_USER` and `GRAFANA_ADMIN_PASSWORD` in `.env`.

## Files

- Dashboard JSON: `grafana/dashboards/*.json`
- Datasource provisioning: `grafana/provisioning/datasources/postgres.yml`
- Dashboard provider provisioning: `grafana/provisioning/dashboards/dashboards.yml`
- Generator: `dashboards/grafana_dashboards.py`

## Validation

```bash
make dashboards-check
```

The validation checks that each dashboard is provisioning-ready, has panels,
uses the `mpesa-postgres` datasource, and contains SQL-backed targets.

## Operational Notes

- Run `make transform` before opening dashboards so dbt marts are current.
- Containers use `postgres:5432`; host tooling uses `localhost:${POSTGRES_HOST_PORT}`.
- Live Daraja checks still require real provider credentials and
  `VERIFY_LIVE_DARAJA=true`.
