# Go infrastructure monitor

Runs configurable HTTP health checks every 15 seconds and serves a read-only snapshot at `GET /v1/health/targets`. The snapshot endpoint requires `X-PesaGuard-Internal-Token`; `GET /healthz` is a liveness endpoint.

Required environment: `CHECK_TARGETS` as comma-separated `name=https://host/healthz` entries, and `INTERNAL_TOKEN` of at least 32 characters. Optional `PORT` defaults to 8083.

Target URLs are trusted operator configuration, not user input. Restrict outbound network access to approved hosts to mitigate SSRF and lateral movement. This endpoint is intended for internal operations; a public status site must consume a separate authenticated/filtered API and must not reveal private hostnames or internal failure details.
