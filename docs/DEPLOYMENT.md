# M-Pesa Real-Time Transaction Streaming - Deployment Guide

## Local Development Setup

### Prerequisites

- Docker & Docker Compose (latest version)
- Python 3.9+
- Git
- 8GB RAM minimum
- 20GB disk space

### Quick Start

#### 1. Clone and Configure

```bash
git clone https://github.com/your-org/mpesa-streaming.git
cd mpesa-streaming/01_MPESA_Safaricom/01_Real_Time_Transaction_Streaming

# Create .env file
cp .env.example .env

# Edit .env with your Daraja credentials
nano .env
```

#### 2. Start Services

```bash
# Start all services
docker-compose up -d

# Verify all services are running
docker-compose ps

# Check logs
docker-compose logs -f
```

#### 3. Initialize Database

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d mpesa -f scripts/init_db.sql

# Run dbt initialization
docker-compose exec dbt dbt debug
docker-compose exec dbt dbt seed
```

#### 4. Test Webhook Receiver

```bash
# Check if webhook is running
curl http://localhost:5000/health

# Send test webhook
curl -X POST http://localhost:5000/webhooks/c2b/validation \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/c2b_validation.json
```

#### 5. Access Services

- **Airflow**: http://localhost:8080 (admin/airflow)
- **Jupyter**: http://localhost:8888 (token required)
- **pgAdmin**: http://localhost:5050 (admin@pgadmin.org/admin)
- **Kafka Manager**: http://localhost:9000

---

## Production Deployment

### Prerequisites

- Kubernetes cluster (EKS, GKE, or AKS)
- Container registry (ECR, GCR, or ACR)
- RDS PostgreSQL instance
- MSK (Managed Streaming for Kafka) or equivalent
- TLS certificates
- Domain name with DNS records

### Architecture Overview

```yaml
Namespace: mpesa-streaming

Deployments:
  - webhook-receiver (replicas: 3)
  - kafka-consumer (replicas: 2)
  - flink-jobmanager (replicas: 1)
  - flink-taskmanager (replicas: 4)
  - airflow-webserver (replicas: 2)
  - airflow-scheduler (replicas: 1)

StatefulSets:
  - postgres (replicas: 1) [if using internal DB]

Services:
  - webhook-receiver (LoadBalancer)
  - airflow-webserver (LoadBalancer)
  - prometheus (ClusterIP)
```

### Step 1: Prepare Infrastructure

#### AWS Example (Terraform)

```hcl
# VPC and networking
module "vpc" {
  source = "./modules/vpc"
  cidr_block = "10.0.0.0/16"
}

# EKS Cluster
module "eks" {
  source = "./modules/eks"
  cluster_name = "mpesa-streaming-prod"
  node_groups = 2
  instance_type = "m5.xlarge"
}

# RDS PostgreSQL
module "rds" {
  source = "./modules/rds"
  engine = "postgres"
  engine_version = "15.0"
  instance_class = "db.r5.xlarge"
  storage_gb = 100
  multi_az = true
  backup_retention_days = 30
}

# MSK (Managed Kafka)
module "msk" {
  source = "./modules/msk"
  broker_nodes = 3
  instance_type = "kafka.m5.large"
  storage_gb = 500
}
```

### Step 2: Build Container Images

```bash
# Build webhook receiver image
docker build -f Dockerfile.webhook -t webhook-receiver:latest .
docker tag webhook-receiver:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/webhook-receiver:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/webhook-receiver:latest

# Build other images similarly
# - flink-job
# - airflow-scheduler
```

### Step 3: Create Kubernetes Manifests

```yaml
---
# deployment-webhook.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webhook-receiver
  namespace: mpesa-streaming
spec:
  replicas: 3
  selector:
    matchLabels:
      app: webhook-receiver
  template:
    metadata:
      labels:
        app: webhook-receiver
    spec:
      containers:
      - name: webhook-receiver
        image: 123456789.dkr.ecr.us-east-1.amazonaws.com/webhook-receiver:latest
        ports:
        - containerPort: 5000
        env:
        - name: DARAJA_CONSUMER_KEY
          valueFrom:
            secretKeyRef:
              name: daraja-credentials
              key: consumer-key
        - name: DARAJA_CONSUMER_SECRET
          valueFrom:
            secretKeyRef:
              name: daraja-credentials
              key: consumer-secret
        - name: KAFKA_BROKERS
          value: "kafka-broker-1:9092,kafka-broker-2:9092,kafka-broker-3:9092"
        - name: POSTGRES_HOST
          value: "mpesa-db.c1234567.us-east-1.rds.amazonaws.com"
        resources:
          requests:
            cpu: 1
            memory: 512Mi
          limits:
            cpu: 2
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 5
      autoscaling:
        minReplicas: 3
        maxReplicas: 10
        targetCPUUtilizationPercentage: 70

---
# service-webhook.yaml
apiVersion: v1
kind: Service
metadata:
  name: webhook-receiver-svc
  namespace: mpesa-streaming
spec:
  type: LoadBalancer
  selector:
    app: webhook-receiver
  ports:
  - protocol: TCP
    port: 443
    targetPort: 5000
```

### Step 4: Deploy to Kubernetes

```bash
# Create namespace
kubectl create namespace mpesa-streaming

# Create secrets
kubectl create secret generic daraja-credentials \
  --from-literal=consumer-key=$DARAJA_KEY \
  --from-literal=consumer-secret=$DARAJA_SECRET \
  -n mpesa-streaming

# Apply manifests
kubectl apply -f k8s/
kubectl apply -f k8s/deployments/
kubectl apply -f k8s/services/

# Verify deployment
kubectl get pods -n mpesa-streaming
kubectl get svc -n mpesa-streaming
```

### Step 5: Configure Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mpesa-ingress
  namespace: mpesa-streaming
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - webhooks.yourdomain.com
    secretName: mpesa-tls
  rules:
  - host: webhooks.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: webhook-receiver-svc
            port:
              number: 443
```

### Step 6: Setup Monitoring

```bash
# Install Prometheus
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  -n mpesa-streaming

# Install Grafana
helm repo add grafana https://grafana.github.io/helm-charts
helm install grafana grafana/grafana \
  -n mpesa-streaming \
  --set adminPassword=CHANGE_ME

# Port forward for access
kubectl port-forward svc/prometheus 9090 -n mpesa-streaming
kubectl port-forward svc/grafana 3000 -n mpesa-streaming
```

---

## Scaling Checklist

### Horizontal Scaling

- [ ] Configure horizontal pod autoscaling (HPA)
- [ ] Set CPU/memory requests and limits
- [ ] Test with load (e.g., `ab -c 100 -n 10000 http://webhooks.yourdomain.com/health`)
- [ ] Monitor pod distribution across nodes
- [ ] Increase Kafka partitions if needed

### Vertical Scaling

- [ ] Monitor CPU/memory usage
- [ ] Increase node instance types if needed
- [ ] Scale PostgreSQL (increase instance class)
- [ ] Scale Kafka brokers
- [ ] Test performance after scaling

### Database Optimization

- [ ] Create indexes on hot columns (phone_number, received_at)
- [ ] Partition tables by date range
- [ ] Archive old data (> 90 days) to S3
- [ ] Monitor query performance
- [ ] Configure connection pooling (pgbouncer)

### Kafka Optimization

- [ ] Increase partitions (consider rebalancing cost)
- [ ] Enable log compaction for state topics
- [ ] Monitor broker disk usage
- [ ] Tune producer/consumer batch sizes
- [ ] Configure cleanup policies

---

## Health Checks

### Liveness Check
```bash
curl http://localhost:5000/health
# Returns: { "status": "healthy", "timestamp": "2026-05-14T12:00:00Z" }
```

### Readiness Check
```bash
curl http://localhost:5000/ready
# Returns: { "kafka": "connected", "database": "connected", "ready": true }
```

### Detailed Health Report
```bash
curl http://localhost:5000/health/full
# Returns comprehensive health metrics
```

---

## Disaster Recovery

### Backup Procedure

```bash
# PostgreSQL backup
pg_dump mpesa > backup_$(date +%Y%m%d_%H%M%S).sql

# Kafka backup (if using persistent storage)
tar -czf kafka_data_$(date +%Y%m%d_%H%M%S).tar.gz /var/lib/kafka

# Flink savepoint
flink savepoint <jobid> hdfs:///savepoints/
```

### Recovery Procedure

```bash
# 1. Restore PostgreSQL
psql mpesa < backup_YYYYMMDD_HHMMSS.sql

# 2. Restore Flink state
flink restore hdfs:///savepoints/savepoint-xxx

# 3. Restart Airflow DAG
airflow dags backfill -s 2026-05-14 -e 2026-05-15 mpesa_real_time_streaming

# 4. Verify data consistency
SELECT COUNT(*) FROM mpesa_transactions_raw;
```

---

## Rollback Procedure

### Application Rollback

```bash
# Get previous version
kubectl rollout history deployment/webhook-receiver -n mpesa-streaming

# Rollback to previous version
kubectl rollout undo deployment/webhook-receiver -n mpesa-streaming

# Verify
kubectl get pods -n mpesa-streaming
```

### Database Rollback

```bash
# If schema changed
psql mpesa -f migrations/rollback_20260514.sql

# Restore from backup if needed
pg_restore mpesa < backup_20260513_180000.sql
```

---

## Performance Tuning

### Connection Pooling

```python
# Set optimal pool size
min_connections = num_workers * 2
max_connections = num_workers * 4

# pgbouncer config
[databases]
mpesa = host=localhost port=5432 user=postgres password=xxx pool_mode=transaction

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
```

### Kafka Tuning

```properties
# Producer config
batch.size=32768
linger.ms=10
compression.type=snappy

# Consumer config
fetch.min.bytes=1024
session.timeout.ms=30000
max.poll.records=500
```

### Database Query Optimization

```sql
-- Add indexes
CREATE INDEX idx_transactions_phone ON mpesa_transactions_raw(phone_number);
CREATE INDEX idx_transactions_received ON mpesa_transactions_raw(received_at DESC);

-- Analyze query plans
EXPLAIN ANALYZE
SELECT COUNT(*) FROM mpesa_transactions_raw
WHERE received_at > NOW() - INTERVAL '1 hour';
```

---

## Cost Optimization

### Compute Optimization
- Use reserved instances for predictable workloads
- Use spot instances for non-critical jobs (Flink TaskManagers)
- Right-size instances based on actual usage

### Storage Optimization
- Archive transactions > 90 days to S3 Glacier
- Use Kafka log compaction for state topics
- Enable PostgreSQL autovacuum

### Network Optimization
- Use VPC endpoints to avoid NAT gateway costs
- Enable VPC Flow Logs for debugging only when needed
- Co-locate services in same AZ when possible

---

## Troubleshooting Common Issues

### OOM Errors
```bash
# Check memory usage
kubectl top pods -n mpesa-streaming

# Increase memory limits
kubectl set resources deployment webhook-receiver \
  -n mpesa-streaming \
  --limits=memory=2Gi
```

### Kafka Connection Issues
```bash
# Test connectivity
kafka-broker-api-versions.sh --bootstrap-server kafka:9092

# Check broker logs
docker-compose logs kafka
```

### Database Slow Queries
```sql
-- Find slow queries
SELECT query, mean_time FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

### High CPU Usage
```bash
# Profile CPU usage
kubectl top pods -n mpesa-streaming --sort-by=cpu

# Check hot spots
perf record -F 99 -p <pid>
perf report
```

---

## Maintenance Schedule

### Daily
- Monitor error rates and latency
- Check health endpoints
- Review logs for warnings

### Weekly
- Run data quality checks
- Review Kafka lag
- Analyze performance trends

### Monthly
- Review and rotate credentials
- Update dependencies
- Analyze cost trends

### Quarterly
- Full disaster recovery drill
- Performance benchmarking
- Capacity planning

---

## Support & Escalation

- **Level 1 (Alerts)**: Automated to Slack/email
- **Level 2 (Investigation)**: On-call engineer (via PagerDuty)
- **Level 3 (Emergency)**: Lead engineer + DevOps team
- **SLA**: Critical (1 hour), High (4 hours), Medium (8 hours)
