# PesaGuard Docker platform

This repository now has per-platform Compose files and one root Compose entry point. These are **local development scaffolds**, not a production deployment or a claim that every service integration is complete.

## One command for the combined local platform

Requires Docker Engine and Docker Compose v2.20.3 or newer (the root file uses Compose `include`).

```sh
docker compose -f compose.yaml config
docker compose -f compose.yaml build
docker compose -f compose.yaml up -d
docker compose -f compose.yaml ps
docker compose -f compose.yaml logs -f
```

Stop containers while preserving local volumes:

```sh
docker compose -f compose.yaml down
```

Remove containers and local development data (destructive):

```sh
docker compose -f compose.yaml down -v
```

## Per-platform stacks

Run a single platform stack from the repository root:

```sh
docker compose -f Infrastructure/compose.yaml up -d
docker compose -f python-compose.yaml up -d --build
docker compose -f Java/compose.yaml up -d --build
docker compose -f Elixir/compose.yaml up -d --build
docker compose -f Go/compose.yaml up -d --build
docker compose -f frontend/compose.yaml up -d --build
```

The platform-specific stacks assume the relevant shared dependencies are available on their Docker network. For cross-platform integration, use the root umbrella file so Compose includes the shared Postgres, Redis and Redpanda services.

## Local ports

- Shared dependencies: PostgreSQL `127.0.0.1:5433`, Redis `127.0.0.1:6380`, Redpanda Kafka `127.0.0.1:19092`.
- Python ingestion: `127.0.0.1:8080`.
- Java services: `127.0.0.1:8100` through `8119`.
- Elixir services: `127.0.0.1:8200` through `8209`.
- Go services: `127.0.0.1:8300` through `8302`.
- Frontends: `127.0.0.1:8401` through `8406`.

## Important limitations

- The root Compose file includes all 20 Java services, 10 Elixir services, 3 Go services, 6 frontends, Python ingestion and local dependencies. This can require substantial RAM, CPU and disk; build one platform at a time if the machine is constrained.
- The existing Python app entry point and environment requirements may need local project-specific configuration; this Compose file uses the existing root Dockerfile and does not migrate the existing runtime package.
- Java and Elixir services are generated scaffolds. Building or starting a container does not mean the service has working business endpoints, health checks, database migrations, auth, or event integration.
- The Go relay needs its Go-owned outbox schema applied to its intended database and must not be pointed at the existing Python outbox until ownership/schema are audited. The relay does not create outbox rows itself.
- The Go quota engine is not automatically inserted into the Java gateway request path. The monitor is internal and must not be exposed directly to the public status website.
- All development credentials/defaults are local-only. Do not reuse them in staging or production. Do not expose these ports to the internet.
- Existing root `docker-compose.yml` remains the original streaming project's stack. Use `docker compose -f compose.yaml ...` explicitly for this combined PesaGuard stack to avoid unintentionally launching both stacks.
- No production resource or traffic was changed. CI and image builds still need to pass before treating this as a verified runnable stack.
