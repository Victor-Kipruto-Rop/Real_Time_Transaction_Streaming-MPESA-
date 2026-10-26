# PesaGuard Go workspace

Go services here are infrastructure components, not a second transaction ledger. Python remains the initial M-Pesa callback/stream-ingestion owner; the existing PesaGuard backend must be audited before any transaction-domain writes are enabled.

## Services

- `services/event-relay`: at-least-once publisher for the Go-owned transactional outbox table. The outbox row must be inserted in the same database transaction as the producer's business change. It does not automatically read or mutate the existing Python outbox.
- `services/quota-engine`: Redis-backed atomic fixed-window quota check for authenticated internal gateway calls. Tenant/environment/key/route values must be derived by the trusted gateway after authentication, never accepted directly from browsers.
- `services/infrastructure-monitor`: configurable HTTP dependency checks and a protected read-only health snapshot. Configure targets explicitly; never expose internal target details publicly without an API-side filter.

## Local development

Each service is a separate Go module. Go 1.23+ is required. Run from the repository root:

```sh
go test ./services/event-relay/...
go test ./services/quota-engine/...
go test ./services/infrastructure-monitor/...
```

For modules with external dependencies, the first run needs network access to download Go modules. Configure secrets via environment variables; never commit real credentials.

## Safety and reliability boundaries

- This workspace does not originate, confirm, reverse, refund, settle, or move payments.
- Relay delivery is at-least-once: a crash after broker acknowledgement but before the database update can publish a duplicate. Consumers must be idempotent.
- Malformed outbox payloads are moved to a durable dead-letter table; operators need audited replay tooling before replay is enabled.
- Redis is not the source of truth. A Redis outage must fail closed for quota enforcement unless a separately approved policy says otherwise.
- Use private networking, TLS, service identity/mTLS or short-lived workload identity, managed secrets, and least-privilege database roles in production. The shared internal token in this starter is a bootstrap guard, not a complete production identity system.
- No service is wired into production traffic by this change. Validate schema compatibility, run integration tests against disposable dependencies, and stage rollout before any routing change.
