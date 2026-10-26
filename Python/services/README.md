# Python service catalog

TELIXO defines ten planned Python service boundaries. Each service has its own README design contract. See [the catalog](../docs/SERVICE_CATALOG.md) and [architecture](../docs/ARCHITECTURE.md).

1. `transaction-ingestion`
2. `reconciliation-engine`
3. `data-quality`
4. `risk-scoring`
5. `stream-processing`
6. `batch-processing`
7. `analytics-metrics`
8. `feature-engineering`
9. `data-enrichment`
10. `model-evaluation-monitoring`

A directory or design document is not proof of a runnable implementation. Before a service is production-ready it needs an agreed contract, single data owner, threat model, migration plan, health/telemetry, tests, container build and CI. Legacy modules stay until staged migration and verification pass.
