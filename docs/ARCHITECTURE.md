# M-Pesa Analytics Platform - Architecture Documentation

## Table of Contents

- [System Overview](#system-overview)
- [Architecture Diagram](#architecture-diagram)
- [Components](#components)
- [Data Flow](#data-flow)
- [Technology Stack](#technology-stack)
- [Design Patterns](#design-patterns)
- [Scalability](#scalability)
- [Security Architecture](#security-architecture)
- [Disaster Recovery](#disaster-recovery)

---

## System Overview

The M-Pesa Analytics Platform is a real-time data engineering system designed to process mobile money transactions at scale. It implements a modern event-driven architecture with the following characteristics:

- **Real-time Processing**: Sub-second latency for transaction ingestion
- **Scalable**: Handles 10,000+ transactions per second
- **Reliable**: 99.9% uptime with automatic failover
- **Secure**: End-to-end encryption and compliance with financial regulations
- **Observable**: Comprehensive monitoring and alerting

### Key Capabilities

1. **Transaction Ingestion**: Receive webhooks from Safaricom Daraja API
2. **Stream Processing**: Real-time event processing with Apache Kafka
3. **Data Transformation**: SQL-based transformations with dbt
4. **Analytics**: Advanced analytics and fraud detection
5. **Visualization**: Real-time dashboards with Grafana

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL SYSTEMS                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────┐         ┌──────────────────┐                 │
│  │  Safaricom       │         │   Mobile Users   │                 │
│  │  Daraja API      │         │   (STK Push)     │                 │
│  └────────┬─────────┘         └────────┬─────────┘                 │
│           │                             │                            │
└───────────┼─────────────────────────────┼────────────────────────────┘
            │                             │
            │ HTTPS Webhooks              │ API Requests
            │                             │
┌───────────▼─────────────────────────────▼────────────────────────────┐
│                      INGESTION LAYER                                  │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │              Webhook Receiver (Flask)                          │  │
│  │  - Rate Limiting (120 req/min)                                 │  │
│  │  - Authentication & Validation                                 │  │
│  │  - Duplicate Detection (Redis)                                 │  │
│  └──────────────────────┬─────────────────────────────────────────┘  │
│                         │                                             │
└─────────────────────────┼─────────────────────────────────────────────┘
                          │
                          │ Produce Events
                          │
┌─────────────────────────▼─────────────────────────────────────────────┐
│                    STREAMING LAYER                                     │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                    Apache Kafka                                   │ │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │ │
│  │  │ mpesa-         │  │ mpesa-         │  │ mpesa-         │    │ │
│  │  │ transactions   │  │ transactions   │  │ transactions   │    │ │
│  │  │ (Partition 0)  │  │ (Partition 1)  │  │ (Partition 2)  │    │ │
│  │  └────────────────┘  └────────────────┘  └────────────────┘    │ │
│  │                                                                   │ │
│  │  ┌────────────────┐                                              │ │
│  │  │ Dead Letter    │  (Failed Messages)                          │ │
│  │  │ Queue (DLQ)    │                                              │ │
│  │  └────────────────┘                                              │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                         │                                              │
└─────────────────────────┼──────────────────────────────────────────────┘
                          │
                          │ Consume Events
                          │
┌─────────────────────────▼──────────────────────────────────────────────┐
│                   PROCESSING LAYER                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │              Kafka Consumer / Flink Processor                   │    │
│  │  - Event Enrichment                                             │    │
│  │  - Data Validation                                              │    │
│  │  - Fraud Detection (ML)                                         │    │
│  │  - Aggregations                                                 │    │
│  └──────────────────────┬──────────────────────────────────────────┘   │
│                         │                                               │
└─────────────────────────┼───────────────────────────────────────────────┘
                          │
                          │ Write to Storage
                          │
┌─────────────────────────▼───────────────────────────────────────────────┐
│                     STORAGE LAYER                                        │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    │
│  │   PostgreSQL    │    │   Redis Cache   │    │   BigQuery      │    │
│  │   (Primary DB)  │    │   (Hot Data)    │    │   (Analytics)   │    │
│  │                 │    │                 │    │                 │    │
│  │  - Transactions │    │  - Sessions     │    │  - Historical   │    │
│  │  - Customers    │    │  - Dedup Cache  │    │  - Aggregates   │    │
│  │  - Metadata     │    │  - Rate Limits  │    │  - ML Features  │    │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    │
│                                                                           │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    │
                                    │ Read Data
                                    │
┌───────────────────────────────────▼───────────────────────────────────────┐
│                   TRANSFORMATION LAYER                                     │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────┐     │
│  │                         dbt (Data Build Tool)                     │     │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │     │
│  │  │  Staging       │  │  Intermediate  │  │  Marts         │    │     │
│  │  │  Models        │  │  Models        │  │  (Analytics)   │    │     │
│  │  └────────────────┘  └────────────────┘  └────────────────┘    │     │
│  │                                                                   │     │
│  │  - Data Quality Tests                                            │     │
│  │  - Incremental Models                                            │     │
│  │  - Documentation                                                 │     │
│  └──────────────────────────────────────────────────────────────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │
┌───────────────────────────────────▼───────────────────────────────────────┐
│                   ANALYTICS & ML LAYER                                     │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────────────────┐    ┌────────────────────────────┐        │
│  │   Advanced Analytics       │    │   ML Models                │        │
│  │   - Customer Segmentation  │    │   - Fraud Detection        │        │
│  │   - Trend Analysis         │    │   - Anomaly Detection      │        │
│  │   - Forecasting            │    │   - Risk Scoring           │        │
│  └────────────────────────────┘    └────────────────────────────┘        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │
┌───────────────────────────────────▼───────────────────────────────────────┐
│                   PRESENTATION LAYER                                       │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────────────────┐    ┌────────────────────────────┐        │
│  │   Grafana Dashboards       │    │   REST API                 │        │
│  │   - Executive Dashboard    │    │   - Query Endpoints        │        │
│  │   - Operations Dashboard   │    │   - Admin Endpoints        │        │
│  │   - Fraud Dashboard        │    │   - Webhook Endpoints      │        │
│  │   - Customer Intelligence  │    │   - Analytics API          │        │
│  └────────────────────────────┘    └────────────────────────────┘        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │
┌───────────────────────────────────▼───────────────────────────────────────┐
│                   MONITORING & OBSERVABILITY                               │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐             │
│  │  Prometheus    │  │  Alertmanager  │  │  ELK Stack     │             │
│  │  (Metrics)     │  │  (Alerts)      │  │  (Logs)        │             │
│  └────────────────┘  └────────────────┘  └────────────────┘             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. Webhook Receiver (Flask Application)

**Purpose**: Receive and validate M-Pesa transaction webhooks

**Key Features**:
- RESTful API endpoints for C2B, STK Push callbacks
- Request validation and sanitization
- Rate limiting (120 requests/minute)
- Duplicate transaction detection using Redis
- Authentication via Bearer tokens
- Health check endpoint

**Technology**: Python Flask, Redis

**Scaling**: Horizontal scaling with load balancer

---

### 2. Apache Kafka (Message Broker)

**Purpose**: Reliable, scalable event streaming

**Configuration**:
- **Topic**: `mpesa-transactions`
- **Partitions**: 3 (for parallel processing)
- **Replication Factor**: 3 (production)
- **Retention**: 7 days

**Key Features**:
- At-least-once delivery guarantee
- Message ordering within partitions
- Consumer groups for parallel processing
- Dead Letter Queue (DLQ) for failed messages

---

### 3. Kafka Consumer / Stream Processor

**Purpose**: Process events from Kafka and write to database

**Processing Steps**:
1. Deserialize JSON messages
2. Validate data schema
3. Enrich with additional data
4. Detect duplicates
5. Run fraud detection
6. Write to PostgreSQL
7. Update cache

**Technology**: Python, Apache Flink (optional)

---

### 4. PostgreSQL Database

**Purpose**: Primary data store for transactions

**Schema**:
```sql
-- Raw transactions table
CREATE TABLE mpesa_transactions_raw (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(50) UNIQUE NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    phone_number VARCHAR(15) NOT NULL,
    account_reference VARCHAR(50),
    transaction_time TIMESTAMP NOT NULL,
    first_name VARCHAR(50),
    middle_name VARCHAR(50),
    last_name VARCHAR(50),
    bill_ref_number VARCHAR(50),
    org_account_balance DECIMAL(15,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_transaction_time ON mpesa_transactions_raw(transaction_time);
CREATE INDEX idx_phone_number ON mpesa_transactions_raw(phone_number);
CREATE INDEX idx_transaction_id ON mpesa_transactions_raw(transaction_id);
```

**Optimization**:
- Connection pooling (10-50 connections)
- Query result caching
- Partitioning by date (monthly)
- Regular VACUUM and ANALYZE

---

### 5. Redis Cache

**Purpose**: High-speed caching and deduplication

**Use Cases**:
- Transaction deduplication (TTL: 24 hours)
- Rate limiting counters
- Session management
- Query result caching (TTL: 5 minutes)
- OAuth token caching

---

### 6. dbt (Data Transformation)

**Purpose**: SQL-based data transformations

**Models**:
```
models/
├── staging/
│   └── stg_transactions.sql
├── intermediate/
│   ├── int_customer_metrics.sql
│   └── int_daily_aggregates.sql
└── marts/
    ├── fct_transactions.sql
    ├── dim_customers.sql
    └── agg_daily_summary.sql
```

**Features**:
- Incremental models for efficiency
- Data quality tests
- Documentation generation
- Lineage tracking

---

### 7. Grafana Dashboards

**Purpose**: Real-time monitoring and analytics

**Dashboards**:
1. **Executive Command Center**: High-level KPIs
2. **Live Operations**: Real-time transaction monitoring
3. **Fraud Risk**: Fraud detection and alerts
4. **Customer Intelligence**: Customer behavior analysis
5. **Data Quality**: Data quality metrics

---

## Data Flow

### Transaction Processing Flow

```
1. M-Pesa Transaction Initiated
   ↓
2. Safaricom sends webhook to /webhook/c2b/confirmation
   ↓
3. Webhook Receiver validates request
   ↓
4. Check for duplicate (Redis)
   ↓
5. Produce message to Kafka topic
   ↓
6. Kafka Consumer receives message
   ↓
7. Enrich transaction data
   ↓
8. Run fraud detection
   ↓
9. Write to PostgreSQL
   ↓
10. Update Redis cache
   ↓
11. dbt transforms data (scheduled)
   ↓
12. Grafana displays metrics
```

### Data Latency

- **Webhook to Kafka**: < 100ms
- **Kafka to Database**: < 500ms
- **End-to-End**: < 1 second
- **Dashboard Update**: 5-10 seconds

---

## Technology Stack

### Backend
- **Language**: Python 3.11
- **Web Framework**: Flask 2.3
- **Async**: asyncio, aiohttp

### Data Processing
- **Message Broker**: Apache Kafka 3.5
- **Stream Processing**: Apache Flink 1.17 (optional)
- **Batch Processing**: Apache Airflow 2.6

### Storage
- **Primary Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Data Warehouse**: Google BigQuery (optional)

### Transformation
- **dbt**: 1.5+
- **SQL**: PostgreSQL dialect

### Monitoring
- **Metrics**: Prometheus
- **Visualization**: Grafana
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **Tracing**: Jaeger (optional)

### Infrastructure
- **Containerization**: Docker 20.10+
- **Orchestration**: Kubernetes 1.27+ / Docker Compose
- **IaC**: Terraform 1.5+
- **CI/CD**: GitHub Actions

---

## Design Patterns

### 1. Event-Driven Architecture

All components communicate via events (Kafka messages), enabling:
- Loose coupling
- Scalability
- Fault tolerance
- Replay capability

### 2. CQRS (Command Query Responsibility Segregation)

- **Write Path**: Webhook → Kafka → Database
- **Read Path**: API → Cache → Database

### 3. Circuit Breaker

Prevents cascading failures:
```python
@circuit_breaker(failure_threshold=5, timeout=60)
def call_external_api():
    # API call
    pass
```

### 4. Retry with Exponential Backoff

For transient failures:
```python
@retry(max_attempts=3, backoff=exponential)
def process_transaction():
    # Processing logic
    pass
```

### 5. Dead Letter Queue (DLQ)

Failed messages sent to DLQ for manual review

---

## Scalability

### Horizontal Scaling

**Webhook Receiver**:
- Deploy multiple instances behind load balancer
- Stateless design enables easy scaling
- Target: 10+ instances for 100K req/min

**Kafka Consumers**:
- Scale by adding consumers to consumer group
- Each consumer processes different partitions
- Target: 1 consumer per partition

**Database**:
- Read replicas for query load
- Partitioning for large tables
- Connection pooling

### Vertical Scaling

- Increase CPU/RAM for compute-intensive tasks
- SSD storage for database
- Dedicated hardware for Kafka brokers

### Auto-Scaling

```yaml
# Kubernetes HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: webhook-receiver-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: webhook-receiver
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

## Security Architecture

### Network Security

- **TLS/SSL**: All external communication encrypted
- **VPC**: Private network for internal services
- **Security Groups**: Restrict access by IP/port
- **WAF**: Web Application Firewall for API

### Application Security

- **Authentication**: Bearer token authentication
- **Authorization**: Role-based access control (RBAC)
- **Input Validation**: Strict schema validation
- **Rate Limiting**: Prevent abuse
- **SQL Injection Prevention**: Parameterized queries

### Data Security

- **Encryption at Rest**: Database encryption
- **Encryption in Transit**: TLS 1.3
- **PII Masking**: Phone numbers masked in logs
- **Audit Logging**: All access logged

### Compliance

- **PCI-DSS**: Payment card industry standards
- **GDPR**: Data protection regulations
- **Kenya Data Protection Act**: Local compliance

---

## Disaster Recovery

### Backup Strategy

**Database Backups**:
- **Frequency**: Daily full backup, hourly incremental
- **Retention**: 30 days
- **Location**: S3 with cross-region replication
- **Testing**: Monthly restore tests

**Kafka Backups**:
- **Replication**: 3x replication factor
- **Snapshots**: Daily topic snapshots
- **Retention**: 7 days in Kafka, 30 days in S3

### Recovery Procedures

**RTO (Recovery Time Objective)**: 1 hour
**RPO (Recovery Point Objective)**: 15 minutes

**Failover Process**:
1. Detect failure (automated monitoring)
2. Promote standby database to primary
3. Update DNS/load balancer
4. Verify system health
5. Resume operations

### High Availability

- **Multi-AZ Deployment**: Services across availability zones
- **Load Balancing**: Distribute traffic across instances
- **Health Checks**: Automatic failover on failure
- **Database Replication**: Synchronous replication

---

## Performance Optimization

### Caching Strategy

- **L1 Cache**: Application memory (LRU, 1GB)
- **L2 Cache**: Redis (10GB)
- **L3 Cache**: Database query cache

### Database Optimization

- **Indexes**: Strategic indexing on query patterns
- **Partitioning**: Monthly partitions for large tables
- **Connection Pooling**: Reuse connections
- **Query Optimization**: EXPLAIN ANALYZE for slow queries

### Kafka Optimization

- **Batch Processing**: Process messages in batches
- **Compression**: Snappy compression for messages
- **Partitioning**: Distribute load across partitions

---

## Future Enhancements

1. **Machine Learning Pipeline**: Real-time ML predictions
2. **GraphQL API**: Flexible query interface
3. **Multi-Region Deployment**: Global availability
4. **Blockchain Integration**: Immutable audit trail
5. **Mobile SDK**: Direct integration for apps

---

## References

- [Kafka Documentation](https://kafka.apache.org/documentation/)
- [PostgreSQL Best Practices](https://www.postgresql.org/docs/current/performance-tips.html)
- [dbt Documentation](https://docs.getdbt.com/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Safaricom Daraja API](https://developer.safaricom.co.ke/)
