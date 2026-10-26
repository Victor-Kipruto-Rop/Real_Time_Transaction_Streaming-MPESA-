# PesaGuard Infrastructure Platform

Shared integration foundation for the six Vite frontends, Java services, Elixir/Phoenix services and existing Python streaming subsystem. This is an architecture/configuration baseline, not a production deployment.

## What connects the platforms
- Browser apps use one public API origin through the Java API Gateway; internal service hostnames are never exposed to browsers.
- OIDC identity and tenant membership are resolved server-side. Every service enforces authorization; client-supplied tenant IDs and roles are not trusted.
- Services communicate through authenticated internal APIs or versioned events. No service reads another service's private tables.
- Producers use durable outbox delivery; consumers use idempotent inbox/deduplication; poison messages go to a durable DLQ with replay controls.
- OpenTelemetry carries correlation IDs, metrics, traces and redacted logs across gateway, services and workers.
- Secrets are injected from a secret manager/runtime environment, never committed or embedded in Vite assets.

## Frontend routing
| Application | Path | Intended host | Access |
|---|---|---|---|
| Public website | frontend/public-website | pesaguard.co.ke | Public routes |
| Tenant dashboard | frontend/tenant-dashboard | app.pesaguard.co.ke | Authenticated, tenant-scoped |
| Admin dashboard | frontend/admin-dashboard | admin.pesaguard.co.ke | Privileged, MFA, audited |
| Developer platform | frontend/developer-platform | developers.pesaguard.co.ke | Developer scopes, sandbox/production separation |
| Docs | frontend/docs-website | docs.pesaguard.co.ke | Public documentation |
| Status | frontend/status-website | status.pesaguard.co.ke | Public, read-only real monitoring data |

These are intended hosts, not proof of live DNS, TLS or deployed apps.

## Service ownership
Python initially owns existing M-Pesa callback/stream ingestion. Java owns platform APIs and proposed domain boundaries. Elixir/Phoenix handles concurrent delivery, workflow and operational workers. PostgreSQL is durable storage per service owner; a broker is not a replacement for transactional persistence. Redis is ephemeral cache/coordination only where recovery semantics are defined.

Audit the existing api.pesaguard backend before choosing a canonical transaction store. There must be exactly one authoritative transaction owner before new transaction writes are enabled.

## Local development
`compose.yaml` runs local PostgreSQL, Redis and Redpanda only. From this directory, run `docker compose up -d`. Credentials are deliberately local-only and must never be reused in staging/production. Ports bind to loopback. This compose stack is not production infrastructure.

## Rollout gates
Validate contracts/catalog; build all workspaces in CI; provision TLS/private networking/managed storage/secrets/backups/monitoring; verify OIDC and cross-tenant denial; failure-test outbox/inbox, retries, DLQ and replay; run staging load/security and restore/rollback tests; obtain explicit approval before production traffic changes.
