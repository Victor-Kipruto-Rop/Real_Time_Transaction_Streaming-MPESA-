# PesaGuard Go workspace

Go services here are infrastructure components, not a second transaction ledger. Python remains the initial M-Pesa callback/stream-ingestion owner; the existing PesaGuard backend must be audited before any transaction-domain writes are enabled.

## Services

- `services/event-relay`: at-least-once publisher for the Go-owned transactional outbox table. The outbox row must be inserted in the same database transaction as the producer's business change. It does not automatically read or mutate the existing Python outbox.
- `services/quota-engine`: Redis-backed atomic fixed-window quota check for authenticated internal gateway calls. Tenant/environment/key/route values must be derived by the trusted gateway after authentication, never accepted directly from browsers.
- `services/infrastructure-monitor`: configurable HTTP dependency checks and a protected read-only health snapshot. Configure targets explicitly; never expose internal target details publicly without an API-side filter.

## Docker

Build and start the three Go infrastructure containers locally (ports 8300–8302):

```sh
docker compose -f Go/compose.yaml up -d --build
docker compose -f Go/compose.yaml ps
```

For the combined platform use `docker compose -f compose.yaml up -d --build` from the repository root. See [`DOCKER_PLATFORM.md`](../DOCKER_PLATFORM.md). The outbox migration must be applied before the relay can work; the quota engine is not yet connected to the gateway.

## Local development

Run commands from the `Go/` directory with Go 1.23+:

```sh
go test ./services/event-relay/...
go test ./services/quota-engine/...
go test ./services/infrastructure-monitor/...
```

The first run for modules with external dependencies needs network access to download Go modules. Configure secrets via environment variables; never commit real credentials.

## Safety and reliability boundaries

- This workspace does not originate, confirm, reverse, refund, settle, or move payments.
- Relay delivery is at-least-once: a crash after broker acknowledgement but before the database update can publish a duplicate. Consumers must be idempotent.
- Malformed outbox payloads and exhausted retries are designed to go to a durable dead-letter table; replay tooling is not yet included.
- Redis is not the source of truth. A Redis outage fails closed for quota enforcement.
- Use private networking, TLS, service identity/mTLS or short-lived workload identity, managed secrets, and least-privilege database roles in production. The shared internal token in this starter is a bootstrap guard, not a complete production identity system.
- The monitor checks only explicitly configured targets. Restrict outbound network access to approved hosts.
- No service is wired into production traffic by this change. Validate schema compatibility, run integration tests against disposable dependencies, and stage rollout before any routing change.
