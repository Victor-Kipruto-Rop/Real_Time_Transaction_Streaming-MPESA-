# TELIXO

TELIXO is a multi-language fintech streaming and infrastructure platform for ingesting, validating, processing, and analyzing M-Pesa transaction events. It does not treat callback receipt as proof of payment, and this repository does not itself initiate, reverse, refund, or settle payments.

## Repository layout

The application and platform code is organized into six top-level platform directories:

| Directory | Responsibility |
|---|---|
| `Python/` | Callback ingestion, event normalization, Kafka streaming, data quality, dbt/analytics, risk research, and Python tests |
| `Java/` | Java enterprise and core service scaffolds |
| `Elixir/` | Concurrent delivery and workflow service scaffolds |
| `Infrastructure/` | Local dependencies, deployment assets, Kubernetes/Terraform, observability, shared event contracts, and platform documentation |
| `frontend/` | Web applications and frontend build/deployment configuration |
| `Go/` | Event relay, quota engine, and infrastructure monitoring services |

GitHub automation remains in `.github/` because GitHub Actions requires that path. Repository-level configuration and entry-point files (for example `.env.example`, `compose.yaml`, Dockerfiles, and `Makefile`) remain at the root; they are not additional application platform directories.

Legacy Python runtime and data-engineering paths have been grouped under `Python/`. Shared contracts, operational documentation, and infrastructure tooling have been grouped under `Infrastructure/`. When changing these locations, update imports, Docker build contexts, Compose mounts, workflow paths, and deployment manifests together.

## Local development

Use Docker Compose v2.20.3 or newer for the combined platform configuration, which uses Compose `include`.

Validate the complete Compose model before starting containers:

```bash
docker compose -f compose.yaml config
```

Build and start the combined local stack:

```bash
docker compose -f compose.yaml build
docker compose -f compose.yaml up -d
docker compose -f compose.yaml ps
```

Stop the stack:

```bash
docker compose -f compose.yaml down
```

Individual platform stacks can be started from the repository root:

```bash
docker compose -f Infrastructure/compose.yaml up -d
docker compose -f python-compose.yaml up -d --build
docker compose -f Java/compose.yaml up -d --build
docker compose -f Elixir/compose.yaml up -d --build
docker compose -f Go/compose.yaml up -d --build
docker compose -f frontend/compose.yaml up -d --build
```

The existing root Dockerfiles use the repository root as the Docker build context and explicitly copy the relevant code from `Python/`. Do not change the build context without updating the corresponding Dockerfile paths.

## Event delivery and financial safety

- Use durable acceptance and retry/recovery semantics for callbacks and published events.
- Describe delivery as at-least-once unless stronger guarantees are proven end-to-end; downstream consumers must be idempotent.
- Persist malformed-message dead letters before advancing a consumer offset.
- Do not treat validation callbacks as confirmation of a financial transaction.
- Do not trust an unverified callback field as tenant identity.
- Never commit production credentials, access tokens, or customer payloads.
- Do not deploy structural changes to production until CI, migration compatibility, and staging smoke tests pass.

## Validation status

A repository reorganization is not proof that all services build or are production-ready. Run the relevant CI workflows and Compose validation after structural changes, review failures, and record which integration tests were skipped because dependencies or provider test credentials were unavailable.
