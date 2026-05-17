<p align="center">
  <img src="./a_high_resolution_infographic_diagram_poster_for_a.png" alt="M-Pesa Real-Time Streaming Pipeline" width="100%">
</p>

# M-Pesa Real-Time Transaction Streaming Pipeline

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

# Technologies Used

- Python
- Apache Kafka
- Apache Flink
- PostgreSQL
- Google BigQuery
- dbt
- Grafana
- Docker
- Airflow
- Safaricom Daraja API

---

# Quick Start

## Clone Repository

```bash
git clone https://github.com/kipruto45/mpesa_safaricom-pipeline-.git
cd mpesa_safaricom-pipeline-
```

## Start Services

```bash
make docker-up
```

## Health Check

```bash
curl -s http://localhost:5000/health | python -m json.tool
```

## Send Sample Transaction

```bash
curl -s -X POST http://localhost:5000/webhook/c2b/confirmation \
  -H 'Content-Type: application/json' \
  -d '{"TransID":"TXN123","TransAmount":"500","MSISDN":"254712345678","AccountReference":"ACC001","TransTime":"20260514120000"}'
```

---

# Verified Features

- Real-time Kafka streaming
- Webhook ingestion
- PostgreSQL insertion
- dbt transformations
- Dockerized infrastructure
- Automated testing
- Analytics-ready data models

---

# Author

Victor Kipruto

GitHub: https://github.com/kipruto45
