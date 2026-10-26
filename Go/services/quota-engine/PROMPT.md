# Quota Engine — Production Engineering Prompt

## Mission and authority

Act as a principal Go security and distributed-rate-limiting engineer. Harden only the quota-engine service and its directly related tests/contracts. Begin by reading the current code, Redis script, gateway integration contracts, Docker Compose configuration and tests. Preserve the existing service boundary and do not invent a gateway integration that is not present.

The service performs an atomic quota decision for a **trusted, authenticated internal gateway**. It is not an identity provider, API-key validator, billing engine, or public endpoint. It must not trust tenant, environment, API-key, route, plan or limit values supplied directly by an untrusted browser or API client.

## Non-negotiable security invariants

1. **Trusted identity context:** the gateway authenticates the caller and derives tenant ID, API-key ID, environment, normalized route and applicable policy. The quota service accepts requests only over private networking with authenticated service identity. The current shared internal token is bootstrap protection only—not production-grade workload identity.
2. **Environment separation:** sandbox and production counters must be cryptographically/structurally isolated in Redis keys. The authoritative environment comes from the gateway, never from a client-controlled header or body.
3. **Atomicity:** concurrent requests must not bypass limits because of read/increment races. Keep the increment and TTL initialization atomic (Lua or an equivalent Redis primitive).
4. **Fail closed:** if Redis is unavailable, malformed, timing out, or returns an ambiguous error, do not grant an unverified request. Return a bounded 503 response and emit a safe operational signal.
5. **Policy authority:** never allow a caller to raise its own quota by choosing `limit` or `windowSeconds`. In production the gateway or trusted policy source must supply an authenticated, validated policy; explicitly document the current contract and do not silently treat user-provided limits as authoritative.
6. **No secrets or PII in keys/logs:** hash or HMAC stable identifiers in Redis keys; never log API keys, tokens, raw authorization headers, full request bodies or connection strings.
7. **Abuse resistance:** enforce request-size limits, strict JSON decoding, unknown-field rejection, timeouts, input bounds, rate limiting at the edge and safe errors. Do not reflect internal exceptions to callers.
8. **No payment authority:** quotas can allow or deny API request capacity only. They must never initiate, approve, reject, refund, reverse, settle or move money.

## Required design

- Document the quota algorithm and its tradeoffs. Fixed windows can permit boundary bursts; do not claim smooth token-bucket behavior. If changing algorithm, define migration compatibility and avoid accidentally resetting existing counters.
- Define the key dimensions explicitly: tenant, environment, API key, normalized route and policy version where needed. Use an unambiguous encoding before hashing to prevent concatenation collisions.
- Validate identity fields, canonical route format, environment, limits and window bounds. Reject missing, overlong, control-character and malformed values.
- Treat policy configuration as trusted input with bounded values. Add a policy version or explicit policy source contract so rollout and debugging are reproducible.
- Use Redis TLS/authentication in production, ACLs with least privilege, network isolation, secret rotation and bounded dial/read/write timeouts. Never ship development fallback secrets in a production configuration.
- Keep health/liveness cheap. Add readiness that checks Redis only when appropriate, and never leak Redis topology or credentials.
- Return stable response schemas and status codes: 2xx allowed, 429 quota exceeded, 400 invalid contract, 401/403 failed service authentication/authorization, 503 dependency failure. Include a retry/reset hint only when it is correct and does not expose sensitive data.
- Add structured logs and metrics for decisions, Redis latency/errors, denials and fail-closed events. Keep high-cardinality tenant/API-key/route identifiers out of metric labels; use bounded dimensions and safe correlation IDs.
- Ensure HTTP server read-header, read, write and idle timeouts; graceful shutdown; request cancellation; and no goroutine leaks.
- Add explicit tests for the trusted-gateway contract and a plan to replace the shared-token guard with mTLS/OIDC or short-lived workload identity before production.

## Required tests

- concurrent requests at the exact limit and beyond it;
- two tenants, two API keys, distinct routes and sandbox/production isolation;
- same input repeatedly increments one counter; key construction cannot collide for adversarial delimiter-containing values;
- TTL is set once and does not accidentally extend on every increment;
- invalid or untrusted environment, missing identity, oversized input, unknown fields, malformed JSON and invalid policy;
- Redis down, timeout, script error and ambiguous response all fail closed;
- internal auth missing/wrong token, constant-time comparison behavior, and no secret reflection;
- request cancellation, graceful shutdown and HTTP timeout behavior;
- stable response contract and safe error body;
- fuzz tests for key construction, request validation and JSON boundary handling where useful.

Run `go test ./services/quota-engine/...`, `go test -race ./services/quota-engine/...`, `go vet ./services/quota-engine/...` and integration tests against disposable Redis. Never run destructive tests against shared or production Redis.

## Delivery protocol

Inspect before editing; list risks and assumptions; implement small, testable changes; add regression tests; update README and configuration docs; run the stated commands and report actual output. Do not claim production security while the shared-token model or client-influenced policy authority remains unresolved.

## Definition of done

Quota decisions are atomic under concurrency, sandbox and production are isolated, callers cannot self-grant higher limits, dependency failure is fail-closed, sensitive data is not exposed, policy semantics are documented, and the gateway/service identity contract is tested. Production traffic stays disconnected until trusted identity and policy authority are verified.
