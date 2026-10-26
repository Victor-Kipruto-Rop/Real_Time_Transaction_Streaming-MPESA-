# Architecture

## Role in PesaGuard

This service ingests and streams provider events. It is not the PesaGuard API gateway, tenant directory, canonical financial ledger, reconciliation engine, payment execution service or settlement system.

## Logical flow

```text
Safaricom Daraja callback
  -> callback validation and replay/duplicate controls
  -> durable ingestion receipt + recoverable event publication
  -> Kafka/Redpanda
  -> idempotent streaming consumer and normalization
  -> canonical PesaGuard transaction owner
  -> reconciliation and risk services
  -> authorized PesaGuard APIs, alerts and analytics
```

## State ownership

Streaming-local operational state includes ingestion receipts, outbox delivery state, retry attempts and dead-letter records. Canonical transaction state belongs to the designated PesaGuard transaction service. Reconciliation state belongs to the designated reconciliation service. Analytics models are read models and must not be treated as authoritative financial state.

## Cross-service integration

Use versioned events for asynchronous workflows and authenticated internal HTTP APIs for operations that require synchronous responses. Use a schema registry or equivalent compatibility checks for shared contracts. Each consumer must have idempotent effects and a documented retry, offset and replay policy.

See [PesaGuard integration boundaries](PESAGUARD_INTEGRATION.md) and [repository reorganization](REPOSITORY_REORGANIZATION.md).
