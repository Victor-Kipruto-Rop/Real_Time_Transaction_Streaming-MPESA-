# PesaGuard Backend Integration Boundaries

## Purpose

This repository is the transaction-streaming and provider-ingestion subsystem. It integrates with the existing PesaGuard Python backend and Java microservices through versioned events and authenticated internal APIs. It is not a replacement for the existing backend.

## Service ownership

| Capability | Owning system | Streaming subsystem responsibility |
|---|---|---|
| Public API gateway and customer authentication | PesaGuard gateway/identity services | No direct ownership |
| Tenant, merchant, membership and RBAC | PesaGuard tenant/merchant services | Resolve trusted context through an approved internal contract |
| Daraja callback endpoint | One explicitly selected ingestion deployment | Validate and durably record callback receipt |
| Provider payload normalization | Streaming subsystem | Normalize provider-specific data without inventing fields |
| Canonical transaction record | Designated PesaGuard transaction service | Send accepted events; do not create a competing ledger |
| Reconciliation decision and state | PesaGuard reconciliation service (Java or current designated implementation) | Emit request events only when contractually required |
| Fraud/risk scoring | Designated risk service | Publish a risk-input event or call an authenticated scoring API |
| Analytics and data quality | Analytics/dbt pipelines | Read approved, minimized data and report quality findings |
| API keys and developer access | PesaGuard developer platform | Never issue or validate customer API keys independently |
| Payment execution, reversals and settlement | Explicitly authorized payment service, if implemented | Callback ingestion does not execute these actions |

Before implementation, confirm the canonical transaction owner by inspecting the existing backend. If ownership cannot be proven, integration must stop at a versioned event boundary rather than writing into another service's tables.

## Event processing lifecycle

1. Receive a callback using the configured Daraja endpoint and expected callback contract.
2. Validate payload structure, required fields, content type, request limits and applicable provider authenticity controls. Do not claim a cryptographic signature exists unless the provider contract actually defines it.
3. Resolve tenant/merchant context from trusted server-side configuration and the registered provider configuration. Never trust a tenant identifier from a public callback as authorization.
4. Record a durable ingestion receipt and enforce a database uniqueness constraint for the relevant provider/event idempotency key.
5. Atomically persist the receipt and an outbox event, or use an equivalent mechanism with demonstrable recovery after process/broker failure.
6. Publish the versioned event and track delivery state separately from the initial acceptance state.
7. Consume with bounded retries, idempotent effects, correct offset handling and durable dead-letter storage.
8. Deliver the normalized event to the canonical PesaGuard transaction owner through the agreed event/API contract.
9. Let the owning reconciliation/risk services produce their own results and events.
10. Expose results only through authorized PesaGuard APIs.

A callback acknowledgement should follow the provider's documented contract and the application's durable acceptance policy. Do not acknowledge a callback as durably accepted if the event can be lost after process termination.

## Cross-language contract rules

- Use explicit event names and schema versions; avoid undocumented free-form dictionaries.
- Include an immutable `event_id`, `event_type`, `schema_version`, `correlation_id`, occurrence timestamp and source.
- Include tenant/merchant context only after trusted resolution.
- Use decimal strings or integer minor units for money; never binary floating point.
- Distinguish provider occurrence time, ingestion time and processing time.
- Define which fields may contain personal data and redact them from logs.
- Define consumer idempotency keys and replay behavior.
- Enforce backward-compatibility checks before publishing schema changes.
- Keep secrets, access tokens, API keys and full credentials out of events.
- Restrict topic ACLs and service identities by least privilege.

## Persistence boundaries

The streaming database may own ingestion receipts, outbox rows, delivery attempts, consumer failure records and operational idempotency state. It must not silently become a second canonical transaction database.

If a copy of transaction data is required for analytics, classify it as a read model, define freshness and retention, and prevent it from becoming an alternative source of truth.

## Failure and recovery requirements

- Broker unavailable: accepted outbox rows remain pending and are retried.
- Publish succeeds but acknowledgement is lost: retry is safe because consumers deduplicate by stable event identity.
- Consumer fails: retry according to bounded policy; do not silently commit the failed offset.
- Poison event: persist a sanitized failure record and payload reference, alert operators, and support controlled replay after correction.
- Duplicate callback: return provider-compatible behavior without duplicating business effects.
- Tenant context cannot be resolved: quarantine/reject according to explicit provider contract; never guess a tenant.
- Schema mismatch: route to a controlled compatibility failure path; do not coerce unknown values silently.
- Downstream service unavailable: retain/retry the event without creating duplicate canonical transactions.

## Deployment boundary

The repository's current Dockerfiles, Compose files, Kubernetes manifests, Terraform and GitHub workflows reference existing paths. Keep those paths stable until replacement images and manifests have been built and tested. A code move is not complete until all runtime entry points, import paths, mounts, health checks, CI jobs, Airflow DAGs and deployment manifests are updated.

No production infrastructure or production traffic should be changed as part of a source-tree reorganization pull request.
