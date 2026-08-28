# Service-Level Objectives (SLOs)

This project operates as a real-time fintech event pipeline. The SLOs below define the minimum production expectations for reliability, data quality, and operational response.

## 1. Core SLOs

| Service or flow | SLO | Target | Alert threshold |
| --- | --- | --- | --- |
| Webhook availability | 99.9% monthly uptime | >= 99.9% | < 99.8% or repeated 5xx spikes |
| Webhook latency | 95th percentile response time | < 500 ms | > 750 ms for 5m |
| Transaction processing success | 99.9% valid events processed | >= 99.9% | < 99.8% over 15m |
| Duplicate prevention | 100% of duplicate replay attempts blocked | 100% | any accepted duplicate event |
| Kafka consumer lag | backlog within operational limits | < 200 messages | > 200 for 5m |
| Data freshness | data available within target delay | < 3 minutes | > 10 minutes |
| Database availability | service availability | 99.9% | any sustained DB outage |
| Dead-letter handling | DLQ volume under control | < 1% of processed messages | > 2% sustained |

## 2. Operational interpretation

- Availability is measured from successful webhook handling and database-backed processing path health.
- Latency is measured for the public webhook and internal processing loop, not just API startup time.
- Freshness is measured from the last accepted transaction event to the time it is visible in the pipeline store.
- Duplicate prevention is a critical product guarantee and must remain at 100% for payment events.

## 3. Error budget guidance

The system should tolerate a small, controlled error budget instead of letting repeated failures accumulate.

- Availability budget: 43.8 minutes of downtime per month maximum at 99.9%.
- Latency budget: the p95 latency target stays below 500 ms for the primary webhook path.
- Data freshness budget: no sustained staleness beyond 10 minutes without intervention.
- Duplicate budget: zero tolerated duplicates for processed payment transactions.

## 4. Alerting expectations

The project alerting setup should trigger before the SLO breaches become customer-visible.

- Error rate alert should fire earlier than a production outage.
- Kafka lag alert should fire before backlog impacts processing latency.
- Database and webhook health checks should fail closed and page the on-call engineer.
- A stale data signal should trigger a response before the freshness threshold is exceeded.

## 5. SLO review cadence

Review SLOs and thresholds once per quarter or after any major deployment that changes traffic pattern, message volume, or failure rate. Any threshold change should be paired with a documented operational rationale and a rollback point.
