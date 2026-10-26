# Go service deployment notes

These images are starter deployment artifacts. They are not deployed by this repository change.

## Build from the repository root

Use the module directory as the Docker build context:

```sh
docker build -f Go/services/event-relay/Dockerfile Go/services/event-relay
docker build -f Go/services/quota-engine/Dockerfile Go/services/quota-engine
docker build -f Go/services/infrastructure-monitor/Dockerfile Go/services/infrastructure-monitor
```

## Required runtime wiring

- Event relay: dedicated database credentials, approved Kafka brokers, network policy, and an explicitly reviewed `go_event_outbox` schema. Its producer must write business state and the outbox row in one transaction. It is not wired to the existing Python outbox.
- Quota engine: private Redis connection and a rotated internal credential. Only the authenticated gateway may call the endpoint; the gateway must derive tenant, API key, environment and normalized route from verified identity context.
- Infrastructure monitor: explicit approved `CHECK_TARGETS` and a rotated internal credential. Restrict egress at the network layer. Do not expose its detailed response to the public status website.

Before staging: scan images and dependencies, run integration tests against disposable PostgreSQL/Kafka/Redis, configure TLS/private networking and managed secrets, test shutdown/restarts and dependency outages, and verify logs redact secrets. Do not route production traffic until reviewed and approved.
