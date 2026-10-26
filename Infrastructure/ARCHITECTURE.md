# Platform integration architecture

```text
Public website | Tenant dashboard | Admin dashboard
Developer platform | Docs website | Status website
                         | HTTPS; no browser secrets
                         v
                    Edge / WAF / TLS
                         v
                    Java API Gateway <----> OIDC provider
                         |
             +-----------+-----------+
             |           |           |
          Java APIs  Python API   Public read APIs
             |       + ingestion
             +-----------+-----------+
                         |
                  Durable state + outbox
                         |
                    Versioned broker
                         |
                  +------+------+
                  |             |
              Java workers  Elixir OTP workers
                  |             |
                  +------+------+
                         |
              OpenTelemetry pipeline
                         |
                metrics/logs/traces
```

## Trust zones
- Public: static assets and explicitly public read APIs.
- Edge: TLS, WAF, rate limits, request limits and routing.
- Application: authenticated service identity and per-service authorization.
- Data: private databases, broker, cache and object storage; never browser-accessible.
- Operations: secret management, deployment identity, telemetry and privileged admin.

## Invariants
- All browser APIs use one gateway origin, not internal service URLs.
- Gateway checks do not replace authorization in downstream services.
- Strip untrusted identity/tenant forwarding headers; resolve tenant membership server-side.
- Events carry immutable event ID, type/version, producer, UTC timestamp, correlation ID and authorized tenant scope where applicable.
- Never publish credentials, tokens or unnecessary sensitive payloads.
- Do not acknowledge an inbound callback until its event or outbox entry is durable.
- Redact secrets and sensitive transaction/customer fields from logs and traces.
