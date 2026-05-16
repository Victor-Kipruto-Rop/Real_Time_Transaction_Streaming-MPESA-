# M-Pesa Real-Time Transaction Streaming - Troubleshooting Guide

## Common Issues & Solutions

### Authentication & Credentials

#### Issue: "401 Unauthorized" from Daraja API

**Symptoms:**
```
Error: Invalid access token
HTTP 401 Unauthorized
```

**Root Causes:**
1. Expired token (> 1 hour old)
2. Invalid consumer key/secret
3. Wrong environment (sandbox vs production)

**Solutions:**
```python
# Check token expiry
from ingestion.daraja_client import DarajaClient
client = DarajaClient()
token = client.get_access_token()
print(token)  # If empty, token generation failed

# Verify credentials
import os
print(f"Consumer Key: {os.getenv('DARAJA_CONSUMER_KEY')}")
print(f"Consumer Secret: {os.getenv('DARAJA_CONSUMER_SECRET')}")

# Test API connectivity
client._session.get('https://api.sandbox.safaricom.co.ke/oauth/v1/generate')
```

**Prevention:**
- Rotate credentials every 30 days
- Store credentials in environment variables (not code)
- Use `.env.example` as template
- Enable token refresh before expiry

---

#### Issue: "Invalid consumer key or secret"

**Solutions:**
```bash
# Verify credentials in .env
grep DARAJA .env

# Re-register for sandbox credentials at developer.safaricom.co.ke

# Test with curl
curl -u "consumer_key:consumer_secret" \
  "https://api.sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
```

---

### Webhook Receiver Issues

#### Issue: Webhooks not received

**Symptoms:**
- No transactions appearing in database
- Kafka topic empty
- Health check shows webhook unhealthy

**Troubleshooting:**
```bash
# 1. Verify webhook receiver is running
docker-compose ps | grep webhook
curl http://localhost:5000/health

# 2. Check logs for errors
docker-compose logs webhook-receiver | tail -50

# 3. Verify Kafka connection
docker-compose logs webhook-receiver | grep -i kafka

# 4. Check firewall rules
curl -vv http://localhost:5000/health

# 5. Test with manual webhook
curl -X POST http://localhost:5000/webhooks/c2b/validation \
  -H "Content-Type: application/json" \
  -d '{
    "TransactionType": "Pay Bill Online",
    "TransID": "TEST123",
    "TransAmount": "5000",
    "MSISDN": "254712345678",
    "AccountReference": "TEST",
    "TransTime": "20260514120000",
    "BusinessShortCode": "174379"
  }'
```

**Solutions:**
1. Check webhook URL is registered in Daraja dashboard
2. Ensure HTTPS certificate is valid (no self-signed)
3. Verify IP whitelist doesn't block Safaricom IPs
4. Check firewall rules allow inbound 443

---

#### Issue: Webhook validation fails

**Symptoms:**
```json
{"error": "Invalid phone number format"}
```

**Solutions:**
```python
# Debug validation
from schemas.transaction_schema import C2BValidationPayload
try:
    payload = C2BValidationPayload(**request.json())
except ValueError as e:
    print(f"Validation error: {e}")

# Check phone number format
from schemas.transaction_schema import normalize_ke_phone
phone = normalize_ke_phone("254712345678")  # Should work
phone = normalize_ke_phone("0712345678")    # Should convert to 254712345678
phone = normalize_ke_phone("+254712345678") # Should convert to 254712345678
```

---

### Database Issues

#### Issue: "Could not connect to PostgreSQL"

**Symptoms:**
```
psycopg2.OperationalError: could not connect to server: Connection refused
```

**Troubleshooting:**
```bash
# 1. Check if PostgreSQL is running
docker-compose ps | grep postgres

# 2. Test connection
psql -h localhost -U postgres -d mpesa -c "SELECT 1"

# 3. Check database logs
docker-compose logs postgres | tail -50

# 4. Verify connection string
echo $DATABASE_URL  # or check .env

# 5. Test from container
docker-compose exec kafka-consumer \
  psql -h postgres -U postgres -d mpesa -c "SELECT COUNT(*) FROM mpesa_transactions_raw"
```

**Solutions:**
```bash
# Start/restart PostgreSQL
docker-compose restart postgres

# Check if port 5432 is available
lsof -i :5432

# Increase connection pool if hitting limits
docker-compose exec postgres \
  psql -U postgres -c "ALTER SYSTEM SET max_connections = 200;"
docker-compose restart postgres
```

---

#### Issue: "Duplicate key value violates unique constraint"

**Symptoms:**
```
ERROR: duplicate key value violates unique constraint "mpesa_transactions_raw_pkey"
```

**Explanation:**
Same transaction_id received twice (idempotency issue)

**Solutions:**
```sql
-- Check for duplicates
SELECT transaction_id, COUNT(*)
FROM mpesa_transactions_raw
GROUP BY transaction_id
HAVING COUNT(*) > 1;

-- The consumer uses ON CONFLICT DO NOTHING, so this shouldn't happen
-- If it does, check if batch insert is misconfigured

-- Manual fix (if needed)
DELETE FROM mpesa_transactions_raw
WHERE ctid NOT IN (
  SELECT MIN(ctid) FROM mpesa_transactions_raw
  GROUP BY transaction_id
);
```

---

#### Issue: "Database connection pool exhausted"

**Symptoms:**
```
QueuePool limit exceeded
all (10) connections are in use
```

**Solutions:**
```python
# Check pool size configuration
from streaming.kafka_consumer import ConsumerConfig
config = ConsumerConfig()
print(config.max_pool_size)

# Increase pool size
os.environ['DB_POOL_MAX_SIZE'] = '20'

# Monitor connections
psql -h localhost -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# Kill idle connections
psql -h localhost -U postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity \
   WHERE state = 'idle' AND query_start < now() - interval '10 minutes';"
```

---

### Kafka Issues

#### Issue: "Failed to connect to Kafka broker"

**Symptoms:**
```
KafkaError: _ALL_BROKERS_DOWN
```

**Troubleshooting:**
```bash
# 1. Check if Kafka is running
docker-compose ps | grep kafka

# 2. Verify broker connectivity
nc -zv localhost 9092

# 3. Check broker logs
docker-compose logs kafka | tail -50

# 4. List topics
docker-compose exec kafka kafka-topics.sh \
  --list --bootstrap-server localhost:9092

# 5. Check broker configuration
docker-compose exec kafka cat /etc/kafka/server.properties
```

**Solutions:**
```bash
# Restart Kafka
docker-compose restart kafka zookeeper

# Check advertised listeners
docker-compose exec kafka cat /etc/kafka/server.properties | grep advertised

# If using Docker, ensure correct hostname
# In KAFKA_ADVERTISED_LISTENERS, use service name (kafka) not localhost
```

---

#### Issue: Consumer lag is very high

**Symptoms:**
```
Consumer lag: 100,000+ messages
```

**Solutions:**
```bash
# 1. Check consumer status
docker-compose exec kafka kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group mpesa_consumer_group \
  --describe

# 2. Increase consumer parallelism
docker-compose up -d --scale kafka-consumer=3

# 3. Increase fetch batch size
# In kafka_consumer.py:
# consumer.poll(max_records=1000, timeout_ms=10000)

# 4. Check database insertion speed
SELECT COUNT(*) FROM mpesa_transactions_raw 
WHERE received_at > NOW() - INTERVAL '1 minute';
# Run multiple times to see throughput
```

---

#### Issue: Kafka message format error

**Symptoms:**
```
json.JSONDecodeError: Expecting value
```

**Solutions:**
```python
# Debug message format
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'mpesa-transactions',
    bootstrap_servers=['localhost:9092']
)

for msg in consumer:
    try:
        data = json.loads(msg.value.decode('utf-8'))
        print(f"Valid: {data}")
    except json.JSONDecodeError as e:
        print(f"Invalid message: {msg.value}")
        print(f"Error: {e}")
```

---

### Apache Flink Issues

#### Issue: "Flink job fails to start"

**Symptoms:**
```
Exception in thread "main" org.apache.flink.api.common.InvalidProgramException
```

**Troubleshooting:**
```bash
# 1. Check Flink logs
docker-compose logs flink-jobmanager | tail -100

# 2. Verify Python/PyFlink installation
docker-compose exec flink-jobmanager python -c "from pyflink.datastream import StreamExecutionEnvironment"

# 3. Check job configuration
cat dags/flink_job.py

# 4. Test locally
python streaming/flink_job.py
```

---

### dbt Issues

#### Issue: "dbt models fail to run"

**Symptoms:**
```
dbt run failed with error
```

**Troubleshooting:**
```bash
# 1. Check dbt logs
dbt debug

# 2. Test database connection
dbt debug --select models/staging/

# 3. Run specific model
dbt run --select stg_mpesa_raw

# 4. Check dbt profiles
cat ~/.dbt/profiles.yml

# 5. Run tests
dbt test --select stg_mpesa_raw
```

**Solutions:**
```bash
# Rebuild profiles
dbt init

# Clear dbt cache
rm -rf target/

# Run with verbose output
dbt run -v

# Parse and validate
dbt parse
```

---

### Performance Issues

#### Issue: High latency (webhook to database > 1 second)

**Diagnose:**
```python
import time
from ingestion.webhook_receiver import app

@app.before_request
def start_timer():
    request.start_time = time.time()

@app.after_request
def end_timer(response):
    duration = time.time() - request.start_time
    print(f"Request took {duration:.3f}s")
    return response
```

**Solutions:**
1. Increase Kafka producer batch size
2. Increase database connection pool
3. Enable query caching
4. Check network latency (ping broker/DB)
5. Profile CPU usage

---

#### Issue: High memory usage

**Diagnose:**
```bash
# Check memory by component
docker stats --no-stream

# Profile memory in Python
python -m memory_profiler streaming/flink_job.py
```

**Solutions:**
1. Reduce Flink state size (enable state compaction)
2. Increase JVM heap for Kafka/Flink
3. Enable garbage collection tuning
4. Batch more messages before processing

---

### Monitoring & Alerting Issues

#### Issue: "No metrics data in Prometheus"

**Solutions:**
```bash
# 1. Check if Prometheus is scraping
curl http://localhost:9090/api/v1/targets

# 2. Check metrics endpoint
curl http://localhost:5000/metrics

# 3. Verify scrape config
cat prometheus.yml | grep -A 5 mpesa

# 4. Check metrics are being recorded
from ingestion.metrics import get_metrics_collector
collector = get_metrics_collector()
collector.record_message_processed()
```

---

### System Resource Issues

#### Issue: "Out of Disk Space"

**Symptoms:**
```
No space left on device
```

**Troubleshooting:**
```bash
# Check disk usage
df -h

# Find large directories
du -sh /* | sort -hr | head -10

# Clean up
docker-compose down
docker system prune -a
docker volume rm $(docker volume ls -qf dangling=true)
```

---

## Debug Mode

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Or via environment variable
export LOG_LEVEL=DEBUG
```

### Health Monitoring Commands

```bash
# Full system health check
curl http://localhost:5000/health/full

# Kafka health
docker-compose exec kafka kafka-broker-api-versions.sh \
  --bootstrap-server localhost:9092

# Database health
docker-compose exec postgres \
  pg_isready -h localhost

# dbt health
docker-compose exec dbt dbt debug

# Airflow health
curl http://localhost:8080/health
```

---

## Getting Help

### Where to Look

1. **Logs**: `docker-compose logs <service>`
2. **Status**: `docker-compose ps`
3. **Database**: Query raw tables with SQL
4. **Kafka**: Use console consumers: `kafka-console-consumer.sh`
5. **Metrics**: Check Prometheus/Grafana dashboards

### Debugging Steps

1. Identify which component failed
2. Check component logs
3. Verify upstream dependencies
4. Test with manual input
5. Check configuration files
6. Review recent changes

### Escalation

- **Level 1**: Check logs and health endpoints
- **Level 2**: Run diagnostic queries/commands
- **Level 3**: Enable debug mode and reproduce
- **Level 4**: Contact Safaricom support (if API issue)
