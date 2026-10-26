# Python services

| Service | Status | Responsibility | Next requirement |
|---|---|---|---|
| `risk-scoring` | Initial extraction | Stateless explainable transaction risk signal | CI tests, source golden-case parity, authenticated internal caller, tenant-scoped history |
| `transaction-ingestion` | Planned | Normalize provider events after trusted callback intake | Map existing ingestion/validator modules and preserve idempotency/outbox |
| `reconciliation` | Planned | Match imported ledger entries with provider transactions | Preserve matching semantics and golden datasets |
| `data-quality` | Planned | Data quality rules, profiling and lineage | Inventory imports and agree data ownership |
| `analytics-reporting` | Conditional | Aggregations and reports that have a clear consumer | Avoid duplicating frontend dashboards or Java reporting |

A directory name is not proof of a production-ready service. Each service must have independent dependency pins, container build, health endpoints, tests, ownership, versioned contracts, configuration documentation and CI.
