# M-Pesa Analytics Platform - Troubleshooting Guide

## Table of Contents

- [Common Issues](#common-issues)
- [Service-Specific Issues](#service-specific-issues)
- [Database Issues](#database-issues)
- [Kafka Issues](#kafka-issues)
- [Webhook Issues](#webhook-issues)
- [Daraja API Issues](#daraja-api-issues)
- [Performance Issues](#performance-issues)
- [Monitoring & Debugging](#monitoring--debugging)
- [Emergency Procedures](#emergency-procedures)

---

## Common Issues

### 1. Services Won't Start

**Symptom**: Docker containers fail to start or immediately exit

**Diagnosis**:
```bash
# Check container status
docker compose ps

# View logs
docker compose logs

# Check specific service
docker compose logs webhook-receiver
```

**Common Causes & Solutions**:

**Port Already in Use**:
```bash
# Find process using port
sudo lsof -i :5000
sudo lsof -i :5432
sudo lsof -i :9092

# Kill process or change port in .env
kill -9 <PID>
```

**Missing Environment Variables**:
```bash
# Verify .env file exists
ls -la .env

# Check for required variables
grep -E "POSTGRES_|KAFKA_|DARAJA_" .env

# Copy from example if missing
cp .env.example .env
```

**Insufficient Resources**:
```bash
# Check Docker resources
docker system df

# Clean up unused resources
docker system prune -a

# Increase Docker memory (Docker Desktop)
# Settings > Resources > Memory: 8GB+
```

---

### 2. Connection Refused Errors

**Symptom**: `Connection refused` or `Cannot connect to service`

**Diagnosis**:
```bash
# Test connectivity
curl http://localhost:5000/health
nc -zv localhost 5432
nc -zv localhost 9092

# Check if services are running
docker compose ps
```

**Solutions**:

**Service Not Ready**:
```bash
# Wait for services to be healthy
docker compose ps
# Look for "healthy" status

# Check health checks
docker inspect webhook-receiver | grep -A 10 Health
```

**Network Issues**:
```bash
# Recreate network
docker compose down
docker network prune
docker compose up -d

# Check network connectivity
docker compose exec webhook-receiver ping postgres
```

**Firewall Blocking**:
```bash
# Check firewall rules (Ubuntu)
sudo ufw status

# Allow ports
sudo ufw allow 5000
sudo ufw allow 5432
sudo ufw allow 9092
```

---

### 3. Authentication Failures

**Symptom**: `401 Unauthorized` or `403 Forbidden`

**Diagnosis**:
```bash
# Test with correct token
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:5000/api/transactions

# Check token in .env
grep UI_TOKEN .env
```

**Solutions**:

**Invalid Token**:
```bash
# Generate new token
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Update .env
echo "UI_TOKEN=new_token_here" >> .env

# Restart services
docker compose restart webhook-receiver
```

**Daraja OAuth Issues**:
```bash
# Test OAuth
python scripts/test_daraja_oauth.py

# Check credentials
grep DARAJA_ .env

# Verify credentials at https://developer.safaricom.co.ke/
```

---

## Service-Specific Issues

### Webhook Receiver Issues

**Problem**: Webhooks not being received

**Diagnosis**:
```bash
# Check webhook logs
docker compose logs -f webhook-receiver

# Test webhook endpoint
curl -X POST http://localhost:5000/webhook/c2b/confirmation \
  -H "Content-Type: application/json" \
  -d '{"TransID":"TEST123","TransAmount":"100","MSISDN":"254712345678"}'
```

**Solutions**:

1. **Check URL Registration**:
```bash
# Verify URLs are registered with Daraja
python scripts/register_daraja_urls.py

# URLs must be HTTPS in production
# Use ngrok for local testing:
ngrok http 5000
```

2. **Rate Limiting**:
```bash
# Check rate limit settings
grep RATE_LIMIT .env

# Increase if needed
echo "RATE_LIMIT_PER_MIN=240" >> .env
docker compose restart webhook-receiver
```

3. **Payload Validation**:
```bash
# Check validation errors in logs
docker compose logs webhook-receiver | grep "validation"

# Test with valid payload
cat examples/sample_transaction.json | \
  curl -X POST http://localhost:5000/webhook/c2b/confirmation \
  -H "Content-Type: application/json" -d @-
```

---

### Kafka Consumer Issues

**Problem**: Messages not being consumed

**Diagnosis**:
```bash
# Check consumer logs
docker compose logs -f kafka-consumer

# Check Kafka topics
docker compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Check consumer group
docker compose exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe --group mpesa_streaming_group
```

**Solutions**:

1. **Consumer Lag**:
```bash
# Check lag
docker compose exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe --group mpesa_streaming_group

# Reset offsets if needed (CAUTION: data loss)
docker compose exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group mpesa_streaming_group \
  --reset-offsets --to-earliest --execute --topic mpesa-transactions
```

2. **Consumer Crashed**:
```bash
# Restart consumer
docker compose restart kafka-consumer

# Check for errors
docker compose logs kafka-consumer | grep -i error

# Increase memory if OOM
# Edit docker-compose.yml:
# deploy:
#   resources:
#     limits:
#       memory: 2G
```

---

## Database Issues

### PostgreSQL Connection Issues

**Problem**: Cannot connect to database

**Diagnosis**:
```bash
# Test connection
psql -h localhost -p 5432 -U data_engineer -d mpesa_analytics

# Check if PostgreSQL is running
docker compose ps postgres

# Check logs
docker compose logs postgres
```

**Solutions**:

1. **Wrong Credentials**:
```bash
# Verify credentials in .env
grep POSTGRES_ .env

# Reset password
docker compose exec postgres psql -U postgres -c \
  "ALTER USER data_engineer WITH PASSWORD 'new_password';"

# Update .env
nano .env
```

2. **Database Not Created**:
```bash
# Create database
docker compose exec postgres psql -U postgres -c \
  "CREATE DATABASE mpesa_analytics;"

# Grant permissions
docker compose exec postgres psql -U postgres -c \
  "GRANT ALL PRIVILEGES ON DATABASE mpesa_analytics TO data_engineer;"
```

3. **Connection Pool Exhausted**:
```bash
# Check active connections
docker compose exec postgres psql -U postgres -c \
  "SELECT count(*) FROM pg_stat_activity WHERE datname='mpesa_analytics';"

# Increase max connections
# Edit postgresql.conf or use environment variable
echo "POSTGRES_MAX_CONNECTIONS=200" >> .env
docker compose restart postgres
```

---

### Database Performance Issues

**Problem**: Slow queries

**Diagnosis**:
```bash
# Check slow queries
docker compose exec postgres psql -U data_engineer -d mpesa_analytics -c \
  "SELECT query, calls, total_time, mean_time 
   FROM pg_stat_statements 
   ORDER BY mean_time DESC LIMIT 10;"

# Check table sizes
docker compose exec postgres psql -U data_engineer -d mpesa_analytics -c \
  "SELECT schemaname, tablename, 
   pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
   FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

**Solutions**:

1. **Missing Indexes**:
```bash
# Create recommended indexes
make db-indexes

# Or manually:
docker compose exec postgres psql -U data_engineer -d mpesa_analytics -c \
  "CREATE INDEX IF NOT EXISTS idx_transaction_time ON mpesa_transactions_raw(transaction_time);
   CREATE INDEX IF NOT EXISTS idx_phone_number ON mpesa_transactions_raw(phone_number);
   CREATE INDEX IF NOT EXISTS idx_transaction_id ON mpesa_transactions_raw(transaction_id);"
```

2. **Vacuum and Analyze**:
```bash
# Run vacuum
docker compose exec postgres psql -U data_engineer -d mpesa_analytics -c \
  "VACUUM ANALYZE mpesa_transactions_raw;"

# Enable autovacuum
docker compose exec postgres psql -U postgres -c \
  "ALTER SYSTEM SET autovacuum = on;"
```

3. **Increase Shared Buffers**:
```bash
# Edit postgresql.conf
docker compose exec postgres bash -c \
  "echo 'shared_buffers = 256MB' >> /var/lib/postgresql/data/postgresql.conf"

docker compose restart postgres
```

---

## Kafka Issues

### Kafka Won't Start

**Problem**: Kafka container exits immediately

**Diagnosis**:
```bash
# Check logs
docker compose logs kafka
docker compose logs zookeeper

# Check if Zookeeper is running
docker compose ps zookeeper
```

**Solutions**:

1. **Zookeeper Not Ready**:
```bash
# Start Zookeeper first
docker compose up -d zookeeper
sleep 10

# Then start Kafka
docker compose up -d kafka
```

2. **Port Conflict**:
```bash
# Check port usage
sudo lsof -i :9092
sudo lsof -i :2181

# Change ports in docker-compose.yml if needed
```

3. **Data Corruption**:
```bash
# Remove Kafka data (CAUTION: data loss)
docker compose down
docker volume rm mpesa_kafka_data
docker compose up -d
```

---

### Topic Issues

**Problem**: Topic not found or messages not persisting

**Diagnosis**:
```bash
# List topics
docker compose exec kafka kafka-topics \
  --list --bootstrap-server localhost:9092

# Describe topic
docker compose exec kafka kafka-topics \
  --describe --topic mpesa-transactions \
  --bootstrap-server localhost:9092
```

**Solutions**:

1. **Create Topic Manually**:
```bash
docker compose exec kafka kafka-topics \
  --create --topic mpesa-transactions \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1
```

2. **Increase Retention**:
```bash
docker compose exec kafka kafka-configs \
  --alter --entity-type topics \
  --entity-name mpesa-transactions \
  --add-config retention.ms=604800000 \
  --bootstrap-server localhost:9092
```

---

## Webhook Issues

### Webhooks Not Received

**Problem**: Daraja webhooks not reaching the application

**Checklist**:
- [ ] URLs registered with Daraja
- [ ] URLs are publicly accessible (HTTPS)
- [ ] Firewall allows incoming connections
- [ ] SSL certificate valid
- [ ] Application is running

**Solutions**:

1. **Test with ngrok (Development)**:
```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com/

# Start tunnel
ngrok http 5000

# Use ngrok URL in Daraja dashboard
# Example: https://abc123.ngrok.io/webhook/c2b/confirmation
```

2. **Verify URL Registration**:
```bash
# Register URLs
python scripts/register_daraja_urls.py

# Test with simulation
python scripts/test_daraja_c2b.py
```

3. **Check Logs for Incoming Requests**:
```bash
# Monitor webhook logs
docker compose logs -f webhook-receiver | grep "POST /webhook"

# Check nginx/load balancer logs if applicable
```

---

## Daraja API Issues

### OAuth Token Errors

**Problem**: `401 Unauthorized` from Daraja API

**Diagnosis**:
```bash
# Test OAuth
python scripts/test_daraja_oauth.py

# Check credentials
grep DARAJA_ .env
```

**Solutions**:

1. **Invalid Credentials**:
```bash
# Verify credentials at https://developer.safaricom.co.ke/
# Update .env with correct values
nano .env

# Test again
python scripts/test_daraja_oauth.py
```

2. **Token Expired**:
```bash
# Tokens expire after 3599 seconds
# Implement token caching in your code
# Check ingestion/daraja_client.py for caching logic
```

3. **Wrong Environment**:
```bash
# Check environment setting
grep DARAJA_ENVIRONMENT .env

# Should be 'sandbox' for testing, 'production' for live
# Update if needed
echo "DARAJA_ENVIRONMENT=sandbox" >> .env
```

---

### C2B Simulation Fails

**Problem**: C2B simulation returns error

**Common Errors**:

**Error: Invalid Shortcode**
```bash
# Verify shortcode
grep DARAJA_C2B_SHORTCODE .env

# Use 174379 for sandbox
echo "DARAJA_C2B_SHORTCODE=174379" >> .env
```

**Error: Invalid Phone Number**
```bash
# Use test numbers for sandbox
# Format: 254XXXXXXXXX
# Example: 254708374149
```

**Error: URLs Not Registered**
```bash
# Register URLs first
python scripts/register_daraja_urls.py

# Then simulate
python scripts/test_daraja_c2b.py
```

---

## Performance Issues

### High CPU Usage

**Diagnosis**:
```bash
# Check container stats
docker stats

# Check process CPU
top -p $(pgrep -f webhook-receiver)
```

**Solutions**:

1. **Optimize Code**:
```bash
# Profile application
python -m cProfile -o profile.stats app/main.py

# Analyze with snakeviz
pip install snakeviz
snakeviz profile.stats
```

2. **Scale Horizontally**:
```bash
# Increase replicas
docker compose up -d --scale webhook-receiver=3
```

3. **Add Resource Limits**:
```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
```

---

### High Memory Usage

**Diagnosis**:
```bash
# Check memory usage
docker stats --no-stream

# Check for memory leaks
docker compose logs webhook-receiver | grep -i "memory"
```

**Solutions**:

1. **Increase Memory Limit**:
```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      memory: 4G
```

2. **Enable Connection Pooling**:
```python
# Ensure connection pooling is enabled
# Check ingestion/db_pool.py
```

3. **Clear Cache**:
```bash
# Clear Redis cache
docker compose exec redis redis-cli FLUSHALL
```

---

## Monitoring & Debugging

### Enable Debug Logging

```bash
# Set log level to DEBUG
echo "LOG_LEVEL=DEBUG" >> .env
docker compose restart

# View logs
docker compose logs -f --tail=100
```

### Access Container Shell

```bash
# Access webhook receiver
docker compose exec webhook-receiver bash

# Access database
docker compose exec postgres psql -U data_engineer -d mpesa_analytics

# Access Kafka
docker compose exec kafka bash
```

### Check Metrics

```bash
# Application metrics
curl http://localhost:5000/metrics

# Database metrics
docker compose exec postgres psql -U data_engineer -d mpesa_analytics -c \
  "SELECT * FROM pg_stat_database WHERE datname='mpesa_analytics';"

# Kafka metrics
docker compose exec kafka kafka-broker-api-versions \
  --bootstrap-server localhost:9092
```

---

## Emergency Procedures

### Complete System Restart

```bash
# Stop all services
docker compose down

# Remove volumes (CAUTION: data loss)
docker compose down -v

# Clean Docker system
docker system prune -a

# Restart
docker compose up -d

# Verify
make verify
```

### Restore from Backup

```bash
# Stop services
docker compose down

# Restore database
./scripts/restore_database.sh backups/mpesa_20260613.sql

# Restart services
docker compose up -d

# Verify data
docker compose exec postgres psql -U data_engineer -d mpesa_analytics -c \
  "SELECT COUNT(*) FROM mpesa_transactions_raw;"
```

### Emergency Rollback

```bash
# See DEPLOYMENT.md for complete rollback procedures
git checkout v0.9.0
docker compose down
docker compose up -d
```

---

## Getting Help

### Collect Diagnostic Information

```bash
# Create diagnostic report
cat > diagnostic_report.txt << EOF
Date: $(date)
Version: $(git describe --tags)
Docker Version: $(docker --version)
Docker Compose Version: $(docker compose version)

Services Status:
$(docker compose ps)

Recent Logs:
$(docker compose logs --tail=50)

Environment:
$(grep -v "PASSWORD\|SECRET\|KEY" .env)
EOF

# Share diagnostic_report.txt when seeking help
```

### Support Channels

- **GitHub Issues**: https://github.com/kipruto45/Real_Time_Transaction_Streaming-MPESA-/issues
- **Documentation**: See docs/ directory
- **Email**: support@your-domain.com
- **Slack**: #mpesa-analytics-support

### Before Reporting Issues

1. Check this troubleshooting guide
2. Search existing GitHub issues
3. Collect diagnostic information
4. Include steps to reproduce
5. Specify your environment (OS, Docker version, etc.)
