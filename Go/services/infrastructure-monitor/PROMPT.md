# Infrastructure Monitor — Production Engineering Prompt

## Mission and authority

Act as a principal Go SRE/security engineer. Harden the infrastructure-monitor service as a read-only, internal operational component. Inspect the existing implementation, target parser, health response, Docker configuration, deployment docs and tests before changing anything.

The monitor probes a fixed operator-configured allowlist of dependencies and serves a sanitized internal snapshot. It is not a general-purpose URL fetcher, public status API, network scanner, vulnerability scanner, or orchestration controller. It must never mutate business data or control payments.

## Non-negotiable security invariants

1. **SSRF containment:** target definitions are trusted deployment configuration only. Reject non-HTTP(S), embedded credentials, unsafe host forms, unapproved domains/IP ranges, unexpected ports and malformed URLs. Protect against loopback, link-local, private-network and cloud metadata endpoints unless a narrowly scoped internal target is explicitly approved by policy. DNS resolution and rebinding must be considered; network egress policy is mandatory defense in depth.
2. **No public topology disclosure:** internal hostnames, addresses, raw URLs, response bodies, credentials and low-level network errors must never appear in public responses. Internal details must be sanitized and access-controlled. A public status page must consume a separately designed filtered API.
3. **Read-only behavior:** the monitor performs only configured health probes. No remediation, restarts, deployments, failover, payments, database writes, or arbitrary command execution.
4. **Bounded work:** enforce target-count limits, per-target timeout, total refresh deadline, bounded concurrency, response-header/body limits and request cancellation. Do not let one slow endpoint block all other checks.
5. **Correct health semantics:** distinguish liveness, readiness, dependency health and stale observations. An empty target set is configuration failure, not healthy. A failed check must not be reported as healthy because an old result remains cached.
6. **Authentication:** protect snapshots and administrative data using private networking and production-grade service identity (mTLS/OIDC or short-lived workload identity). The current shared token is bootstrap-only and must be rotated; do not treat it as a complete production authorization system.
7. **Safe observability:** structured logs and metrics only; no secrets, full URLs with credentials, response bodies, or uncontrolled high-cardinality labels.

## Required design

- Validate target configuration once at startup and fail fast on invalid/duplicate names, excessive target count, unsafe URL syntax and policy violations.
- Use an explicit hostname/domain/IP allowlist and denylist policy with documented exceptions. Resolve DNS safely and validate resolved addresses; avoid time-of-check/time-of-use gaps where practical. Document required network egress rules.
- Probe concurrently with a bounded worker pool. Each check has a strict timeout, request context, redirect policy that cannot escape the allowlist, and response handling that closes bodies without unbounded reads.
- Define health criteria per target: accepted status codes, optional expected content marker without exposing content, TLS verification, and optional latency thresholds. Do not accept every 3xx response as healthy by default.
- Track result freshness, last successful check, consecutive failures, consecutive successes, latency, check duration and sanitized error category. Use a stable schema with versioning if the response is consumed by other services.
- Expose liveness separately from readiness and internal snapshots. Readiness should report stale/missing critical checks accurately; public status must not reuse the raw internal snapshot.
- Make snapshot reads race-safe and immutable to callers. Use defensive copies and test with the race detector.
- Add bounded metrics: check outcome, duration, stale result count, refresh duration and monitor self-health. Do not label metrics with arbitrary target URLs or tenant/customer IDs.
- Provide configurable refresh interval, per-target timeout, maximum concurrency, stale threshold and accepted status ranges, all validated with safe bounds.
- Implement graceful shutdown, cancellation, HTTP server timeouts and predictable startup behavior. Avoid process exit from background goroutines without recording the cause.
- Add operator documentation for target onboarding, allowlist review, incident response, stale-data interpretation, credential rotation and public status redaction.

## Required tests

- valid/invalid target configuration, duplicate names, excessive target count, URL credentials, redirects, malformed schemes, disallowed IPs and metadata-service addresses;
- DNS resolution policy and blocked target behavior;
- slow, hung, unreachable, TLS-invalid and non-success targets;
- concurrency limits and proof that one slow check does not stall unrelated checks;
- stale results, empty configuration, initial startup and refresh cancellation;
- no redirect escape, no response-body leakage and no raw URL/error leakage;
- race tests for concurrent refresh/snapshot access;
- readiness/liveness distinction, shutdown and HTTP timeout behavior;
- response schema stability and sanitized output.

Run `go test ./services/infrastructure-monitor/...`, `go test -race ./services/infrastructure-monitor/...`, `go vet ./services/infrastructure-monitor/...` and network-policy integration tests using controlled mock servers. Tests must not probe arbitrary public or production hosts.

## Delivery protocol

Inspect first and enumerate security gaps. Make small changes with tests. Document allowlist assumptions and any residual SSRF risk. Report only commands actually run and their actual results. Never claim the monitor is production-secure while arbitrary internal destinations remain reachable or raw infrastructure details are exposed.

## Definition of done

Only explicitly approved targets can be probed, probes are bounded and isolated, stale or empty health data cannot look healthy, private topology is protected, the service is race-tested, and operational docs explain the limits of the health signal. Public status exposure remains blocked until a separate redaction contract exists.
