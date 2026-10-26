# TELIXO Python platform

Python owns data processing and intelligence, not a duplicate API gateway or payment execution platform.

## Layout

- `services/risk-scoring/`: first extracted service; stateless, explainable risk assessment.
- `services/transaction-ingestion/`: planned; provider payload normalization and validated internal-event consumption.
- `services/reconciliation/`: planned; tenant-ledger matching and discrepancy outcomes.
- `services/data-quality/`: planned; quality rules, profiling and lineage.
- `workers/`: only asynchronous workers with a documented event owner and idempotent processing contract.
- `shared/`: small, versioned Python-only helpers; cross-language contracts belong under `Infrastructure/contracts/`.
- `MIGRATION_PLAN.md`: source audit, ownership decisions and staged migration checklist.

## Source backend

The source of truth for the migration is the `pesaguard_backend_pipeline` package in `Victor-Kipruto-Rop/api.pesaguard`. Do not copy the whole application as a second runnable monolith. Extract modules with their required tests and dependencies into one service at a time. Keep the source repository and its Alembic history unchanged while parity is being established.

## Local risk service

From `Python/services/risk-scoring`:

```bash
python -m venv .venv
# Activate the virtual environment for your shell.
pip install -r requirements.txt
pip install -e .
pytest -q tests
uvicorn risk_scoring.app:app --app-dir src --host 127.0.0.1 --port 8300
```

- Liveness: `GET /health/live`
- Readiness: `GET /health/ready`
- Risk assessment: `POST /v1/risk/assess`

The service returns an explainable risk signal only. It does not execute or authorize a financial action. Production integration requires authenticated service-to-service access, trusted tenant context, tenant-scoped history retrieval, rate limits, audit events and contract tests.
