# 1. M-Pesa Real-Time Transaction Streaming Pipeline

## Difficulty: Intermediate | Impact: High

### Overview
Connect to Safaricom Daraja C2B and B2C webhooks, stream events through Kafka topics, enrich with merchant category codes, and land cleansed records in BigQuery. Build a live dashboard showing transaction volumes, peak hours, paybill vs till split, and regional heat maps by second.

### Tools Required
- Python
- Apache Kafka
- Apache Flink
- Google BigQuery
- dbt
- Grafana
- Docker

### Kenyan Data Sources
- Safaricom Daraja API (C2B Validation/Confirmation, B2C Result, STK Push Callback)

### Project Structure
```
mpesa-streaming-pipeline/
.env
.gitignore
README.md
requirements.txt
docker-compose.yml # Kafka + Zookeeper + PostgreSQL + Airflow
Makefile
ingestion/
  __init__.py
  daraja_client.py # OAuth token + Daraja API calls
  stk_push.py # Trigger STK Push transactions
  webhook_receiver.py # Flask app: receives C2B/B2C callbacks
  kafka_producer.py # Publishes events to Kafka topic
streaming/
  kafka_consumer.py # Consumes & enriches transaction events
  flink_job.py # PyFlink job for windowed aggregations
schemas/
  transaction_schema.py # Pydantic model for each event type
dbt/models/
  staging/stg_mpesa_raw.sql
  marts/mart_hourly_volumes.sql
  marts/mart_county_heatmap.sql
dags/
  mpesa_batch_dag.py # Hourly dbt run + quality checks
tests/
notebooks/
docs/
```

### Key Deliverables
- Real-time Kafka streams from Daraja webhooks
- Flink enrichment pipeline
- BigQuery tables with cleaned transactions
- Grafana dashboard for monitoring

### Next Steps
1. Set up Kafka cluster
2. Configure Safaricom Daraja API credentials
3. Develop webhook handlers
4. Build Flink transformation jobs
5. Create BigQuery schemas
6. Deploy Grafana dashboards

## Quick run (local)

1) Configure env
- Copy `.env.example` → `.env` and fill values you have. Daraja credentials are only required if you’ll call Daraja APIs (e.g. STK push).

2) Start local dependencies + webhook receiver
```bash
make docker-up
```

3) Health check
```bash
curl -s http://localhost:5000/health | python -m json.tool
```

4) Send a sample confirmation payload (publishes to Kafka when `KAFKA_BROKERS` is set)
```bash
curl -s -X POST http://localhost:5000/webhook/c2b/confirmation \
  -H 'Content-Type: application/json' \
  -d '{"TransID":"TXN123","TransAmount":"500","MSISDN":"254712345678","AccountReference":"ACC001","TransTime":"20260514120000"}'
```

## DBT
This project ships a local dbt config under `dbt/`:
```bash
dbt run --project-dir dbt --profiles-dir dbt
dbt test --project-dir dbt --profiles-dir dbt
```
