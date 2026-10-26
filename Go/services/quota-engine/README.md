# Go distributed quota engine

Internal-only HTTP endpoint `POST /v1/quotas/check` applies an atomic Redis fixed-window counter. It returns 200 when allowed and 429 when the configured limit has been exceeded.

Required environment: `REDIS_URL`, `INTERNAL_TOKEN` (at least 32 characters). Optional `PORT` defaults to 8082. The caller must be the trusted API Gateway and must derive tenant, API key, environment, and normalized route after authentication and authorization. Never expose this endpoint directly to browsers or trust client-supplied identity context.

The bootstrap shared-token guard is not a replacement for workload identity, mTLS/OIDC, secret rotation, or network policy. Redis failure returns 503 (fail closed). Sandbox and production are separated in the counter key; the authoritative key environment must come from the gateway.
