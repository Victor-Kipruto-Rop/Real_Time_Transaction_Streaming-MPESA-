# M-Pesa Real-Time Transaction Streaming - Architecture Guide

## System Overview

The M-Pesa Real-Time Transaction Streaming system is a production-grade data pipeline that ingests, validates, processes, and analyzes M-Pesa transactions in real-time using Safaricom's Daraja API.

### Data Flow Diagram

```
┌──────────────────┐
│  Daraja Webhook  │  M-Pesa events (C2B/B2C/STK callbacks)
└────────┬─────────┘
         │
         ▼
┌──────────────────────────┐
│  Flask Webhook Receiver  │  Ingestion endpoint
│  (Port 5000)             │  - Validates requests
└────────┬─────────────────┘  - Publishes to Kafka
         │
         ▼
┌──────────────────────────┐
│  Kafka Topic             │  mpesa-transactions
│  mpesa-transactions      │  - Partitioned by phone number
└────────┬─────────────────┘  - Retention: 7 days
         │
         ├──────────────┬──────────────┐
         ▼              ▼              ▼
    ┌─────────┐  ┌──────────┐  ┌────────────┐
    │ Consumer │  │Flink Job │  │ Monitoring │
    │ (Batch) │  │ (Stream) │  │  (Alerting)│
    └────┬────┘  └────┬─────┘  └────────────┘
         │            │
         │        ┌───┴────┐
         │        ▼        ▼
         │    ┌──────────────────────┐
         │    │ Windowed Aggregations│
         │    │ - Hourly (tumbling)  │
         │    │ - 15-min (sliding)   │
         │    └──────────┬───────────┘
         │               │
         │    ┌──────────┴───────────┐
         │    │                      │
         ▼    ▼                      ▼
      ┌─────────────────────────────────────┐
      │  PostgreSQL Database                │
      │  - mpesa_transactions_raw (8M rows) │
      │  - Real-time data warehouse        │
      └────────┬────────────────────────────┘
               │
               ▼
      ┌─────────────────────────────┐
      │  dbt Transformations        │
      │  - Staging layer (validation)
      │  - Mart layer (aggregations)│
      └────────┬────────────────────┘
               │
      ┌────────┴────────────────┐
      ▼                         ▼
   ┌─────────────────┐  ┌──────────────────┐
   │ Reporting Views │  │ Real-time Alerts │
   │ & Dashboards    │  │ (Fraud Detection)│
   └─────────────────┘  └──────────────────┘
```

---

## Component Architecture

### 1. Ingestion Layer

**File:** `ingestion/`

- **webhook_receiver.py** - Flask REST API
  - Endpoints: `/c2b/validation`, `/c2b/confirmation`, `/b2c/result`
  - Schema validation using Pydantic
  - Publishes validated events to Kafka

- **daraja_client.py** - Safaricom Daraja API Client
  - OAuth2 token management with caching
  - STK push initiation
  - C2B URL registration
  - Token refresh logic

- **kafka_producer.py** - Kafka Publisher
  - Publishes events to `mpesa-transactions` topic
  - Partition strategy: by phone number (for state locality)
  - Batch configuration: 100 messages or 30 seconds

- **stk_push.py** - STK Push Handler
  - Initiates M-Pesa STK push prompts
  - Handles callbacks and status tracking
  - Persists transaction metadata

### 2. Streaming Layer

**File:** `streaming/`

- **kafka_consumer.py** - Kafka Consumer
  - Consumes from `mpesa-transactions` topic
  - Enriches transactions (phone standardization, county mapping)
  - Batch inserts into PostgreSQL (50-message batches)
  - Connection pooling for efficiency

- **flink_job.py** - Apache Flink Stream Processor
  - Real-time windowed aggregations
  - Window types:
    - **Tumbling 1-hour** windows (for KPIs)
    - **Sliding 15-minute** windows with 5-minute stride
  - State management for velocity detection
  - Anomaly detection (amount bounds, frequency thresholds)
  - Publishes aggregated results back to Kafka

### 3. Data Validation

**File:** `schemas/`

- **transaction_schema.py** - Pydantic Models
  - C2BValidationRequest - incoming webhook validation
  - C2BConfirmationRequest - confirmation handling
  - B2CResultRequest - B2C outcome tracking
  - MpesaEvent - enriched event model

### 4. Transformation Layer

**File:** `dbt/models/`

- **Staging Models** (`staging/`)
  - `stg_mpesa_raw.sql` - Raw data cleansing
  - `stg_c2b_transactions.sql` - C2B-specific transformations
  - Apply business rules and validation

- **Mart Models** (`marts/`)
  - `mart_daily_transactions.sql` - Daily summary metrics
  - `mart_hourly_volumes.sql` - Hourly aggregations
  - `mart_county_heatmap.sql` - Geographic transaction heatmap

### 5. Orchestration Layer

**File:** `dags/`

- **mpesa_streaming_dag.py** - Airflow DAG
  - Scheduled frequency: Hourly
  - Tasks:
    1. Check Kafka connectivity
    2. Run dbt staging transformations
    3. Run dbt mart transformations
    4. Execute data quality tests
    5. Generate fraud alerts
    6. Send notifications

### 6. Monitoring & Alerting

**File:** `ingestion/`

- **health_checks.py** - Health Monitoring
  - Kafka connectivity checks
  - Database connection validation
  - Consumer lag monitoring
  - Transaction volume trending
  - Data staleness detection

- **alerting.py** - Alert Management
  - Slack notifications
  - Email alerts
  - Sentry integration
  - Custom alert templates

- **metrics.py** - Prometheus Metrics
  - Message processing counters
  - Kafka consumer lag gauges
  - Database operation histograms
  - Transaction amount distribution
  - Pipeline health metrics

---

## Data Model

### Source Table

```sql
CREATE TABLE mpesa_transactions_raw (
  transaction_id TEXT PRIMARY KEY,
  phone_number TEXT NOT NULL,
  amount NUMERIC NOT NULL,
  account_reference TEXT,
  transaction_time TEXT,
  received_at TIMESTAMP,
  source TEXT,
  payload JSONB
);

CREATE INDEX idx_phone_number ON mpesa_transactions_raw(phone_number);
CREATE INDEX idx_received_at ON mpesa_transactions_raw(received_at);
CREATE INDEX idx_transaction_time ON mpesa_transactions_raw(transaction_time);
```

### Transformed Tables

**mart_daily_transactions**
- Grain: One row per calendar date
- Contains: Daily transaction counts, totals, averages, unique customer counts

**mart_hourly_volumes**
- Grain: One row per hour
- Contains: Hourly transaction metrics and percentile amounts

**mart_county_heatmap**
- Grain: One row per county per hour
- Contains: County-level transaction volumes and amounts

---

## Kafka Topic Design

### Topic: mpesa-transactions

```
Partitions: 10 (by phone number prefix for locality)
Replication Factor: 3
Retention: 7 days (604,800,000 ms)
Compression: snappy

Message Format:
{
  "event_type": "c2b_validation|c2b_confirmation|b2c_result|stk_callback",
  "transaction_id": "STK123456789",
  "phone_number": "254712345678",
  "amount": "5000",
  "account_reference": "INV001",
  "transaction_time": "20260514120000",
  "received_at": "2026-05-14T12:00:00Z",
  "source": "daraja_webhook",
  "data": { ... }
}
```

### Topic: mpesa-fraud-alerts

```
Partitions: 3
Replication Factor: 3
Retention: 30 days (2,592,000,000 ms)
Compression: snappy

Message Format:
{
  "alert_type": "velocity|amount_threshold|pattern_anomaly",
  "transaction_id": "STK123456789",
  "phone_number": "254712345678",
  "risk_score": 75,
  "reason": "5 transactions in 60 seconds",
  "detected_at": "2026-05-14T12:00:15Z"
}
```

---

## Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| API Framework | Flask | 2.x | REST webhook endpoints |
| Message Queue | Apache Kafka | 7.5.0 | Event streaming |
| Stream Processing | Apache Flink | 1.18.0 | Real-time aggregations |
| Database | PostgreSQL | 15-alpine | Data warehouse |
| Data Transformation | dbt | 1.5+ | SQL transformations |
| Orchestration | Apache Airflow | 2.x | Workflow scheduling |
| Validation | Pydantic | 2.5.0 | Schema validation |
| Monitoring | Prometheus | 2.x | Metrics collection |
| Visualization | Grafana | 9.x | Dashboards |
| Testing | pytest | 7.4+ | Unit testing |
| Container | Docker | Latest | Containerization |

---

## Deployment Architecture

### Local Development

```yaml
Services (Docker Compose):
- PostgreSQL 15 (port 5432)
- Kafka (port 9092)
- Zookeeper (port 2181)
- Flask App (port 5000)
- Airflow Webserver (port 8080)
- Airflow Scheduler
- Jupyter Lab (port 8888)
```

### Production Deployment

```
┌─────────────────────────────────────┐
│   Kubernetes Cluster                │
├─────────────────────────────────────┤
│ ┌─────────────────────────────────┐ │
│ │ Ingestion Service (replicas: 3) │ │
│ │ - Flask app with gunicorn       │ │
│ │ - Auto-scaling on CPU/memory    │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Kafka Cluster (brokers: 5)      │ │
│ │ - High availability             │ │
│ │ - Persistent storage (EBS)      │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Flink Cluster (TaskManagers: 4) │ │
│ │ - Stream processing jobs        │ │
│ │ - State backend: RocksDB        │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ PostgreSQL RDS                  │ │
│ │ - Multi-AZ deployment           │ │
│ │ - Automated backups             │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│ Monitoring & Alerting               │
├─────────────────────────────────────┤
│ - Prometheus (metrics scraping)      │
│ - Grafana (dashboards)              │
│ - PagerDuty (on-call alerts)        │
│ - Sentry (error tracking)           │
│ - CloudWatch (AWS logs)             │
└─────────────────────────────────────┘
```

---

## Performance Characteristics

### Throughput
- **Webhook Receiver**: ~1000 req/sec per instance
- **Kafka Consumer**: ~5000 msgs/sec with batching
- **Flink Processor**: ~10000 events/sec per node
- **Database Insert**: ~1000 transactions/sec with batch

### Latency
- **Webhook to Kafka**: <50ms (p99)
- **Kafka to Consumer**: <100ms (p99)
- **Consumer to Database**: <500ms (p99)
- **End-to-end**: <1s (p99)

### Storage
- **Raw Transactions**: 8M+ rows (~2GB with indexes)
- **Kafka Retention**: 7 days at 1000 msgs/sec = ~600GB
- **Flink State**: <1GB per job (with RocksDB)

---

## Scaling Strategy

### Horizontal Scaling

- **Flask App**: Increase replicas (load balancer distributes)
- **Kafka**: Add brokers and increase partitions
- **Flink**: Increase parallelism (default: 4, max: 16)
- **PostgreSQL**: Read replicas for analytics queries

### Vertical Scaling

- Increase CPU/memory allocation to pods
- Kafka brokers: 32GB+ RAM recommended
- Flink TaskManagers: 16GB+ RAM for state

### Optimization

- Enable compression (Snappy)
- Tune batch sizes (Kafka: 100msgs, DB: 50 records)
- Partition strategy: by phone prefix for locality
- Index optimization: transaction_id (unique), phone_number, received_at

---

## Disaster Recovery

### RTO (Recovery Time Objective): 15 minutes
### RPO (Recovery Point Objective): 1 minute

### Backup Strategy

1. **PostgreSQL**: Automated daily backups + WAL archiving
2. **Kafka**: Replication factor=3 provides fault tolerance
3. **Flink**: Savepoints every 5 minutes
4. **Configuration**: Version controlled in Git

### Recovery Procedures

1. **Database Failure**: Restore from latest backup or read replica
2. **Kafka Failure**: Automatic failover to replicas
3. **Flink Failure**: Resume from last savepoint
4. **Network Partition**: Manual intervention with Kafka reassignment

---

## Cost Optimization

### Resource Allocation
- Flask: 1 CPU, 512MB RAM (per pod)
- Kafka: 2 CPU, 4GB RAM (per broker)
- Flink: 2 CPU, 8GB RAM (per TaskManager)
- PostgreSQL: 4 CPU, 16GB RAM (production tier)

### Cost-saving Measures
- Use spot instances for Flink TaskManagers
- Archive old transactions to S3 (after 90 days)
- Use Kafka log compaction for state topics
- Schedule non-essential jobs (analytics) during off-peak hours
