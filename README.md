# M-Pesa Real-Time Transaction Streaming Pipeline

![M-Pesa Real-Time Streaming Pipeline](a_high_resolution_infographic_diagram_poster_for_a.png)

## Difficulty: Intermediate → Advanced  
## Impact: High  
## Category: Real-Time Data Engineering / FinTech Analytics

---

# Overview

This project demonstrates how modern financial transaction systems process real-time mobile money payments at scale using a production-style data engineering architecture.

The pipeline receives M-Pesa transaction events from Safaricom Daraja API webhooks, streams them through Apache Kafka, processes and enriches the events in real time, stores them in PostgreSQL/BigQuery, and visualizes analytics using dashboards.

The project simulates how real-world payment systems handle:

- Real-time transaction ingestion
- Event streaming
- Data transformation
- Fraud monitoring concepts
- Analytics pipelines
- Monitoring and observability
- Scalable distributed systems

---

# Architecture Flow

```text
Safaricom Daraja API
        ↓
Webhook Receiver (Flask)
        ↓
Kafka Producer
        ↓
Apache Kafka Topic
        ↓
Kafka Consumer / Flink Processing
        ↓
PostgreSQL / BigQuery
        ↓
dbt Transformations
        ↓
Grafana / Streamlit Dashboard
```

---

# Key Features

- Real-time M-Pesa transaction streaming
- Kafka-based event-driven architecture
- Scalable transaction processing pipeline
- Data validation using Pydantic schemas
- Transaction enrichment and transformations
- Analytics-ready warehouse tables
- Dockerized local development setup
- Monitoring and observability support
- dbt data quality testing
- Dashboard visualization for insights

---

# Technologies Used

| Category | Tools |
|---|---|
| Programming | Python |
| Streaming | Apache Kafka |
| Stream Processing | Apache Flink |
| Database | PostgreSQL / BigQuery |
| Data Transformation | dbt |
| Monitoring | Grafana |
| Containerization | Docker |
| Workflow Orchestration | Apache Airflow |
| API Integration | Safaricom Daraja API |

---

# Kenyan Data Sources

## Safaricom Daraja API

This project integrates with:

- C2B Validation API
- C2B Confirmation API
- B2C Result API
- STK Push Callback API

These APIs simulate real mobile money payment workflows used across Kenya.

---

# Project Structure

```bash
mpesa-streaming-pipeline/
│
├── .env
├── .gitignore
├── README.md
├── requirements.txt
├── docker-compose.yml
├── Makefile
│
├── ingestion/
│   ├── __init__.py
│   ├── daraja_client.py
│   ├── stk_push.py
│   ├── webhook_receiver.py
│   └── kafka_producer.py
│
├── streaming/
│   ├── kafka_consumer.py
│   └── flink_job.py
│
├── schemas/
│   └── transaction_schema.py
│
├── dbt/
│   └── models/
│       ├── staging/
│       │   └── stg_mpesa_raw.sql
│       │
│       └── marts/
│           ├── mart_hourly_volumes.sql
│           └── mart_county_heatmap.sql
│
├── dags/
│   └── mpesa_batch_dag.py
│
├── tests/
├── notebooks/
└── docs/
```

---

# Quick Start

## 1. Clone Repository

```bash
git clone https://github.com/kipruto45/mpesa_safaricom-pipeline-.git
cd mpesa_safaricom-pipeline-
```

## 2. Configure Environment Variables

Copy:

```bash
.env.example
```

to:

```bash
.env
```

Add your credentials.

---

## 3. Start Services

```bash
make docker-up
```

This starts:

- Kafka
- ZooKeeper
- PostgreSQL
- Redis
- Airflow
- Webhook Receiver

---

## 4. Health Check

```bash
curl -s http://localhost:5000/health | python -m json.tool
```

---

## 5. Send Sample Transaction

```bash
curl -s -X POST http://localhost:5000/webhook/c2b/confirmation \
  -H 'Content-Type: application/json' \
  -d '{"TransID":"TXN123","TransAmount":"500","MSISDN":"254712345678","AccountReference":"ACC001","TransTime":"20260514120000"}'
```

---

# dbt Transformations

Run transformations:

```bash
dbt run --project-dir dbt --profiles-dir dbt
```

Run tests:

```bash
dbt test --project-dir dbt --profiles-dir dbt
```

---

# Verified Working Features

- Kafka streaming
- Webhook ingestion
- PostgreSQL insertion
- dbt model execution
- End-to-end local data flow
- Dockerized services
- Automated tests

---

# Analytics Dashboard Features

- Transaction volume tracking
- Peak transaction hour analysis
- County transaction heatmaps
- Merchant analytics
- Real-time monitoring
- Data quality checks

---

# Future Improvements

- Google Cloud deployment
- Kubernetes support
- Spark Streaming integration
- ML-based fraud detection
- CI/CD pipelines
- Prometheus monitoring
- Grafana dashboards

---

# Educational Purpose

This project is intended for:

- Learning real-time data engineering
- Demonstrating Kafka streaming concepts
- Understanding financial transaction systems
- Building production-style portfolio projects

---

# Author

## Victor Kipruto

- GitHub: https://github.com/kipruto45
- Project Repository: https://github.com/kipruto45/mpesa_safaricom-pipeline-
