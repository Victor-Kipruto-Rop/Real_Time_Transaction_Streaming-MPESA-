# Python deployable services

TELIXO starts with four Python service boundaries:

- `transaction-ingestion/`: durable consumption and normalization after trusted event acceptance.
- `reconciliation-engine/`: deterministic matching against the canonical ledger interface.
- `data-quality/`: validation, quality findings and quarantine.
- `risk-scoring/`: existing inference service and the sole Python risk-scoring boundary.

Analytics, batch processing, feature engineering and model evaluation remain jobs/libraries until independent scaling or operational ownership justifies another service. Do not add a microservice merely to mirror a folder.

Each deployable service must eventually have a package, dependency policy, Dockerfile, health endpoints, configuration schema, tests, telemetry, migration ownership and service-specific CI. Target-boundary documentation is not proof that legacy code has been migrated or that a service is production-ready.
