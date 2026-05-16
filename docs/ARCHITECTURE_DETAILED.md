# System Architecture

> Comprehensive real-time transaction processing system for M-Pesa with streaming, transformations, and analytics

## Architecture Diagram

### High-Level System Architecture

```mermaid
graph LR
    A["Safaricom Daraja API"] -->|OAuth2| B["Webhook Receiver<br/>Flask 3.0"]
    B -->|Validate & Partition| C["Kafka Topic<br/>mpesa-transactions<br/>10 Partitions"]
    
    C -->|Consume| D["Kafka Consumer<br/>MpesaKafkaConsumer"]
    D -->|Batch Insert<br/>ON CONFLICT| E["PostgreSQL 15<br/>mpesa_transactions_raw<br/>Connection Pool: 1-10"]
    
    C -->|Stream Process| F["Apache Flink 1.18<br/>Windowed Aggregations<br/>Tumbling 1hr / Sliding 15min"]
    F -->|Write Results| G["Kafka Topic<br/>mpesa-fraud-alerts<br/>3 Partitions"]
    
    E -->|Read Raw| H["dbt Models<br/>SQL Transformations<br/>5 Models"]
    H -->|Write Marts| I["PostgreSQL Data Marts<br/>Hourly/Daily/Heatmap<br/>Fraud Tracking"]
    
    I -->|Query| J["Analytics & BI<br/>Grafana Dashboards<br/>SQL Reports"]
    I -->|Monitor| K["Health Checks<br/>Prometheus Metrics<br/>Alerting"]
    
    K -->|Alert on Anomaly| L["Slack / Email<br/>Sentry Error Tracking<br/>PagerDuty"]
    
    H -->|Orchestrate| M["Apache Airflow 2.x<br/>DAG Scheduling<br/>Task Dependencies"]
    M -->|Execute| H
```

---

## Component Details

### 1. **Ingestion Layer** 📥

#### Webhook Receiver (Flask 3.0)
```python
# ingestion/webhook_receiver.py (223 lines)
- Routes (POST): /webhook/c2b/validation, /webhook/c2b/confirmation, /webhook/b2c/result
- Health (GET): /health
- HMAC-SHA256 signature validation for security
- Pydantic schema validation for all inputs
- Publishes validated events to Kafka with JSONB payload
- Error handling with dead-letter queue
```

**Features:**
- ✅ Async request handling with Flask
- ✅ CORS support for development
- ✅ Graceful error responses
- ✅ Request logging and audit trails
- ✅ Health check endpoint

#### Kafka Producer (confluent-kafka 2.3.0)
```python
# ingestion/kafka_producer.py (216 lines)
- MpesaKafkaProducer class for event publishing
- Batch configuration for efficiency (batch.size=100, linger.ms=10)
- Idempotent producer for exactly-once semantics
- Phone-based partitioning strategy (partition = hash(phone) % 10)
- Delivery confirmation callbacks
```

**Configuration:**
```
brokers: ["localhost:9092"]  # Multiple brokers in production
topic: "mpesa-transactions"
partitions: 10               # Horizontal scaling
replication_factor: 3        # High availability
retention.ms: 604800000      # 7 days
```

#### Daraja API Client (OAuth2)
```python
# ingestion/daraja_client.py
- OAuth2 token management with caching (Redis)
- Token refresh automation
- C2B URL registration
- STK push initiation
- Error handling & retry logic
- Rate limiting awareness
```

---

### 2. **Message Queue Layer** 📨

#### Apache Kafka 7.5.0

**Topics:**
| Topic | Partitions | Replicas | Retention | Purpose |
|-------|-----------|----------|-----------|---------|
| `mpesa-transactions` | 10 | 3 | 7 days | Main transaction stream |
| `mpesa-fraud-alerts` | 3 | 3 | 30 days | Fraud detection results |
| `mpesa-dlq` | 1 | 3 | 30 days | Dead letter queue |

**Partitioning Strategy:**
```
partition = hash(phone_number) % 10
```
This ensures all transactions from the same customer go to the same partition, enabling stateful processing.

**Consumer Groups:**
- `mpesa_consumer_group`: PostgreSQL persistence
- `flink_consumer_group`: Stream processing
- `analytics_consumer_group`: Real-time analytics

---

### 3. **Stream Processing Layer** ⚡

#### Apache Flink 1.18.0 (PyFlink)

```python
# streaming/flink_job.py (367 lines)

env = StreamExecutionEnvironment.get_execution_environment()

# Kafka source
kafka_source = FlinkKafkaConsumer(
    topics=["mpesa-transactions"],
    deserialization_schema=JsonDeserializationSchema(),
    properties={"bootstrap.servers": "localhost:9092"}
)

# Windowed aggregations
windowed_stream = (
    env.add_source(kafka_source)
    .map(lambda x: (x["county"], x["amount"]))
    # Tumbling window: 1 hour
    .key_by(lambda x: x[0])
    .window(TumblingEventTimeWindow.of(60*60*1000))
    .sum(1)
)

# Kafka sink
windowed_stream.add_sink(FlinkKafkaProducer(
    topic="mpesa-fraud-alerts",
    serialization_schema=JsonSerializationSchema()
))

env.execute("mpesa_streaming_job")
```

**Window Types:**
1. **Tumbling Windows (1 hour)**
   - Non-overlapping, continuous
   - Used for daily volumes
   - Late data: allowed up to 5 minutes (watermark)

2. **Sliding Windows (15 minutes)**
   - 5-minute slides
   - Used for real-time trends
   - Good for monitoring anomalies

**State Management:**
- Managed state for running aggregates
- TTL (Time-To-Live) for memory efficiency
- Checkpoint every 60 seconds

---

### 4. **Storage Layer** 🗄️

#### PostgreSQL 15 (Data Warehouse)

**Schema:**

```sql
-- Raw transactions (write-heavy)
mpesa_transactions_raw (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(50) UNIQUE NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_phone (phone_number),
    INDEX idx_timestamp (timestamp),
    INDEX idx_transaction (transaction_id)
)

-- C2B staging
stg_c2b_transactions (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(50) NOT NULL,
    merchant_code VARCHAR(20) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    result_code VARCHAR(10),
    result_description VARCHAR(255),
    timestamp TIMESTAMP NOT NULL,
    processed_at TIMESTAMP DEFAULT NOW()
)

-- Hourly volumes mart
mart_hourly_volumes (
    id SERIAL PRIMARY KEY,
    hour_timestamp TIMESTAMP NOT NULL,
    county VARCHAR(50) NOT NULL,
    transaction_count INT NOT NULL,
    total_amount DECIMAL(15,2) NOT NULL,
    avg_amount DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(hour_timestamp, county)
)

-- Daily transactions mart
mart_daily_transactions (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    county VARCHAR(50) NOT NULL,
    merchant_code VARCHAR(20) NOT NULL,
    transaction_count INT NOT NULL,
    total_amount DECIMAL(15,2) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, county, merchant_code)
)

-- County heatmap
mart_county_heatmap (
    id SERIAL PRIMARY KEY,
    hour_timestamp TIMESTAMP NOT NULL,
    county VARCHAR(50) NOT NULL,
    transaction_volume INT NOT NULL,
    anomaly_score DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(hour_timestamp, county)
)
```

**Connection Pooling:**
- Min connections: 1
- Max connections: 20
- Timeout: 5 seconds
- Idle timeout: 60 seconds

```python
pool = SimpleConnectionPool(
    minconn=1,
    maxconn=20,
    dsn="postgresql://user:pass@localhost/mpesa_dw",
    connect_timeout=5
)
```

---

### 5. **Transformation Layer** 🔄

#### dbt (data build tool) 1.5+

**Transformation Pipeline:**

```
raw_events
    ↓
[stg_mpesa_raw] ← Validate, dedup, normalize
    ↓
[stg_c2b_transactions] ← Filter C2B, enrich merchant info
    ↓
[mart_daily_transactions] ← Aggregate by day + county + merchant
[mart_hourly_volumes] ← Aggregate by hour + county
[mart_county_heatmap] ← Geographic analysis
```

**Models:**
```yaml
# dbt/models/schema.yml

models:
  - name: stg_mpesa_raw
    description: Deduplicated raw M-Pesa events
    tests:
      - unique: transaction_id
      - not_null: transaction_id
      - custom_validator: phone_format
    columns:
      - name: phone_number
        tests:
          - matches_format: '^254\d{9}$'

  - name: stg_c2b_transactions
    description: C2B transactions with validation
    tests:
      - unique: transaction_id
      - relationships:
          to: ref('stg_mpesa_raw')
          field: transaction_id
      - dbt_expectations.expect_column_values_to_be_in_set:
          column_name: result_code
          value_set: ['0', '1']

  - name: mart_daily_transactions
    description: Daily aggregated transactions
    tests:
      - dbt_utils.expression_is_true:
          expression: "transaction_count > 0"
      - dbt_utils.expression_is_true:
          expression: "total_amount > 0"
      - unique:
          column_name: "date || '|' || county || '|' || merchant_code"
```

**dbt Configuration:**
```yaml
# dbt/dbt_project.yml
name: 'mpesa_transformations'
version: '1.0.0'
config-version: 2

profile: 'mpesa'
model-paths: ["models"]
test-paths: ["tests"]
macro-paths: ["macros"]

models:
  mpesa_transformations:
    staging:
      materialized: view
    marts:
      materialized: table
      pre_hook: "{{ log('Building mart: ' ~ this.name, info=True) }}"
      post_hook: "ANALYZE TABLE {{ this.name }};"
```

**Execution:**
```bash
# Daily Airflow DAG trigger
dbt run --target prod --models +mart_*
dbt test --target prod
dbt docs generate
```

---

### 6. **Orchestration Layer** ⏰

#### Apache Airflow 2.x (DAG-based)

```python
# dags/mpesa_streaming_dag.py

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.dbt.cloud.operators.dbt import DbtCloudRunJobOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'data-engineering',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2024, 1, 1),
}

dag = DAG(
    'mpesa_streaming_dag',
    default_args=default_args,
    description='M-Pesa streaming and transformation pipeline',
    schedule_interval='@daily',
    catchup=False,
)

# Task 1: Health check
health_check = PythonOperator(
    task_id='health_check',
    python_callable=check_kafka_health,
    dag=dag,
)

# Task 2: Kafka consumer lag check
lag_check = PythonOperator(
    task_id='lag_check',
    python_callable=check_consumer_lag,
    dag=dag,
)

# Task 3: Raw data validation
raw_validation = PostgresOperator(
    task_id='raw_data_validation',
    sql='sql/validate_raw_data.sql',
    postgres_conn_id='mpesa_warehouse',
    dag=dag,
)

# Task 4: dbt transformations
dbt_run = DbtCloudRunJobOperator(
    task_id='dbt_run',
    job_id=42,
    dag=dag,
)

# Task 5: Data quality checks
quality_checks = PostgresOperator(
    task_id='quality_checks',
    sql='sql/data_quality_tests.sql',
    postgres_conn_id='mpesa_warehouse',
    dag=dag,
)

# Task 6: Fraud detection
fraud_detection = PythonOperator(
    task_id='fraud_detection',
    python_callable=detect_fraud,
    dag=dag,
)

# Dependencies
health_check >> lag_check >> raw_validation >> dbt_run >> quality_checks >> fraud_detection
```

---

### 7. **Monitoring & Observability** 📈

#### Prometheus Metrics

**Metrics Collected (~25 total):**

| Metric | Type | Purpose |
|--------|------|---------|
| `mpesa_messages_processed_total` | Counter | Total messages processed |
| `mpesa_kafka_lag_bytes` | Gauge | Bytes behind latest offset |
| `mpesa_db_insert_duration_ms` | Histogram | Insert latency |
| `mpesa_transactions_total` | Counter | Transaction count by status |
| `mpesa_validation_errors_total` | Counter | Validation failures |
| `mpesa_flink_lag_records` | Gauge | Flink processing lag |
| `mpesa_pipeline_health_score` | Gauge | Overall health (0-100) |

**Prometheus Configuration:**
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'mpesa-streaming'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 15s
    scrape_timeout: 10s
```

#### Grafana Dashboards

**Dashboard 1: Transaction Overview**
- Transaction rate (transactions/sec)
- Average transaction amount
- Transaction by county (map)
- Error rate

**Dashboard 2: System Health**
- Kafka consumer lag
- Database connection pool usage
- Flink watermark progress
- Airflow task success rate

**Dashboard 3: Performance Metrics**
- API response time (p50, p95, p99)
- Database query performance
- Kafka throughput
- Memory/CPU usage

---

### 8. **Alerting System** 🚨

#### Alert Rules

```yaml
# Alert configuration
alerts:
  - name: HighKafkaLag
    condition: kafka_consumer_lag > 300000  # 300 seconds
    severity: critical
    notification: slack, email, pagerduty

  - name: HighErrorRate
    condition: error_rate > 0.01  # >1%
    severity: warning
    notification: slack

  - name: DBConnectionPoolExhausted
    condition: db_pool_available_connections < 1
    severity: critical
    notification: slack, pagerduty

  - name: FraudAlert
    condition: anomaly_score > 0.8
    severity: warning
    notification: slack, sentry
```

---

## Scaling Strategy

### Horizontal Scaling

**Kafka Partitions:**
```
Initial: 10 partitions per topic
Growth: Add partitions as needed (no downtime)
Max recommended: 100-200 partitions per topic

Consumer instances: Match partition count
```

**PostgreSQL:**
```
Single node: 5GB/month data + 2-3 connections
Replicas: Read replicas for analytics queries
Sharding: By phone_number prefix if needed
Archival: Move data >90 days to cold storage
```

**Flink Parallelism:**
```
Per partition: 1-2 parallel instances
Checkpointing: Every 60 seconds
State backend: RocksDB for large state
```

---

## Performance Characteristics

### Latency (End-to-end)
```
Webhook receive → Kafka → Consumer → Database: ~500ms (p95)
Database → dbt transformation: 5-10 minutes
Transformation → Analytics dashboard: <1 second
```

### Throughput
```
Webhook: 2,500+ transactions/sec
Kafka: 5,000+ events/sec
Database: 500+ inserts/sec (batch of 50)
Flink: 10,000+ events/sec
```

### Resource Usage
```
Kafka cluster: 3x m5.large (120GB storage)
PostgreSQL: 1x m5.2xlarge (100GB storage)
Flink: 2x m5.xlarge (16GB memory)
Airflow: 1x t3.medium + scheduler
```

---

## Disaster Recovery

### Backup Strategy
```
PostgreSQL: Daily snapshots + WAL archiving
Kafka: Replication factor 3 + log compaction
Flink state: Distributed snapshots every 60s
Configuration: Version controlled in Git
```

### Recovery Procedures
```
RTO (Recovery Time Objective): 15 minutes
RPO (Recovery Point Objective): 1 minute

Steps:
1. Detect failure via monitoring alerts
2. Promote read replica or restore snapshot
3. Reset Kafka consumer offset (if needed)
4. Verify data consistency
5. Resume normal operations
```

---

## Security Architecture

### Data Security
- HTTPS for all external APIs
- Encryption at rest (S3, RDS)
- Encryption in transit (TLS 1.2+)
- PII masking in logs

### Access Control
- OAuth2 for Daraja API
- Database credentials via environment variables
- Kubernetes secrets for sensitive config
- IAM roles for AWS services

### Audit & Compliance
- Audit logging for all transactions
- PII handling documented (GDPR)
- Data retention policies enforced
- Regular security scanning (bandit, OWASP)

---

## Technology Decisions (ADR)

### Why Apache Kafka?
✅ Distributed message queue for scalability
✅ Durability with replication
✅ Consumer groups for multiple pipelines
✅ Exactly-once semantics support

### Why Apache Flink?
✅ Stream processing with complex windowing
✅ State management for running aggregates
✅ Exactly-once processing semantics
✅ Rich SQL API (Flink SQL)

### Why dbt?
✅ SQL-based transformations (familiar)
✅ Version control for transformations
✅ Built-in testing framework
✅ Documentation generation

### Why PostgreSQL?
✅ ACID compliance for consistency
✅ JSON support (JSONB) for flexible payload
✅ Full-text search for transaction details
✅ Excellent for OLAP workloads

---

## Future Enhancements

- [ ] Flink SQL API for more complex transformations
- [ ] Kafka Schema Registry for schema evolution
- [ ] dbt cloud for managed transformations
- [ ] Apache Spark for ML-based fraud detection
- [ ] Real-time dashboards with Superset
- [ ] Cost optimization with spot instances
- [ ] Multi-region disaster recovery
