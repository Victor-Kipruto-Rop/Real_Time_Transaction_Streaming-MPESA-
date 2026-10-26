# Go event relay

Polls the Go-owned PostgreSQL outbox and publishes versioned JSON events to Kafka/Redpanda using synchronous broker acknowledgements.

## Required configuration

- `DATABASE_URL`: private PostgreSQL connection string with least-privilege access to `go_event_outbox` and `go_event_outbox_dead_letters`.
- `KAFKA_BROKERS`: comma-separated broker list.
- Optional: `INSTANCE_ID`, `PORT`, `POLL_INTERVAL`, `BATCH_SIZE`, `MAX_ATTEMPTS`.

Apply `migrations/001_outbox.sql` only to a database designated for this Go-owned outbox. The producer must write its business change and outbox row in one database transaction. Do not point this at the existing Python outbox without auditing and explicitly adapting the schema.

Delivery is at-least-once. A crash between broker acknowledgement and the published marker can cause a duplicate. Consumers must deduplicate by stable event ID. Malformed JSON and exhausted retries are persisted in the dead-letter table; replay should require authorization, audit and a documented operator procedure.
