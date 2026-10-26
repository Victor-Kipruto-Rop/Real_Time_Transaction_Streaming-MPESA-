# Risk Scoring Service

**Priority:** High

**Design responsibility:** Generate explainable risk scores and anomaly signals using approved, versioned features, rules and models.

## Purpose
Produce explainable risk/anomaly signals for transaction and reconciliation records using approved, versioned features and rules/models. This service does not execute financial actions.

## Contract
- **Inputs:** validated event references, approved feature vectors, feature version, model/rule version and trusted tenant context.
- **Outputs:** score, severity, reason codes, model/rule version, feature version, score timestamp, correlation ID and explicit unavailable/error state.
- **Owns:** model/rule metadata, scoring provenance, evaluation references and service-specific scoring state.
- **Must not own:** payment authorization/execution; canonical transaction or tenant records; provider callback intake; reconciliation matching; customer webhook delivery.
- **Dependencies:** Feature Engineering, approved model artifact registry/storage, authorized feature source, telemetry and its own metadata store.

## Safety and reliability
- Never infer a score from missing or invalid inputs without an explicit documented fallback policy.
- Return reason codes and model/rule/feature versions with every successful score.
- Validate artifact integrity and compatibility before loading models.
- Bound inference latency and concurrency; isolate expensive model work from health endpoints.
- Use deterministic, versioned rule fallback only if explicitly approved; clearly mark fallback results.
- Record scores as signals for authorized downstream policy, not as authorization to move funds.
- Protect model artifacts and feature data; enforce tenant scope and avoid sensitive values in logs.
- Provide liveness/readiness, structured logs, metrics, tracing, graceful shutdown and bounded dependency retries.

## Failure behavior
- Invalid schema/features: reject with a reason-coded validation result.
- Model artifact unavailable or invalid: report unavailable; do not fabricate a score.
- Dependency timeout: bounded retry only for safe idempotent reads; otherwise return an explicit retryable error.
- Drift or degraded quality: emit monitoring signals; do not automatically promote/rollback a model without an approved release policy.

## Acceptance tests
- Stable score and reason-code shape across supported schema versions.
- Missing, null, out-of-range and stale features.
- Model artifact signature/checksum and incompatible version.
- Determinism and reproducibility for a pinned model version.
- Tenant-isolation negative tests.
- Latency/load limits and graceful shutdown.
- Approved fallback path clearly marked in response and telemetry.
- Model version rollback and feature-schema migration.
- Sensitive data absent from logs and error messages.

## Build readiness
Before implementation, approve the feature contract with Feature Engineering, the score contract with Java/consumers, the artifact/version policy, data retention, SLO and runbook. The existing code under this directory must be audited against these requirements before it is called production-ready.
