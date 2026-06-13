# M-Pesa Analytics Platform - Deployment Guide

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Local Development Deployment](#local-development-deployment)
- [Staging Deployment](#staging-deployment)
- [Production Deployment](#production-deployment)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Post-Deployment](#post-deployment)
- [Rollback Procedures](#rollback-procedures)

---

## Overview

This guide covers deploying the M-Pesa Analytics Platform across different environments:
- **Local Development**: For development and testing
- **Staging**: Pre-production environment
- **Production**: Live production environment

### Architecture Components

- **Webhook Receiver**: Flask application (Port 5000)
- **Kafka Consumer**: Stream processing service
- **PostgreSQL**: Primary database (Port 5432)
- **Apache Kafka**: Message broker (Port 9092)
- **Redis**: Caching layer (Port 6379)
- **Grafana**: Monitoring dashboards (Port 3000)
- **dbt**: Data transformation

---

## Prerequisites

### System Requirements

**Minimum**:
- CPU: 4 cores
- RAM: 8 GB
- Storage: 50 GB SSD
- OS: Ubuntu 20.04+ / RHEL 8+ / macOS 12+

**Recommended (Production)**:
- CPU: 8+ cores
- RAM: 16+ GB
- Storage: 200+ GB SSD
- OS: Ubuntu 22.04 LTS

### Software Requirements

- Python 3.8+
- Docker 20.10+
- Docker Compose 2.0+
- Git 2.30+
- PostgreSQL 15+ (if not using Docker)
- Apache Kafka 3.0+ (if not using Docker)

### Access Requirements

- Safaricom Daraja API credentials
- AWS account (for RDS, optional)
- GCP account (for BigQuery, optional)
- Domain with SSL certificate (production)
- SSH access to deployment servers

---

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/kipruto45/Real_Time_Transaction_Streaming-MPESA-.git
cd Real_Time_Transaction_Streaming-MPESA-
```

### 2. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit with your configuration
nano .env
```

**Critical Variables**:
```bash
# Daraja API
DARAJA_CONSUMER_KEY=your_consumer_key
DARAJA_CONSUMER_SECRET=your_consumer_secret
DARAJA_BUSINESS_SHORTCODE=174379
DARAJA_PASSKEY=your_passkey
DARAJA_ENVIRONMENT=sandbox  # or 'production'

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mpesa_analytics
POSTGRES_USER=data_engineer
POSTGRES_PASSWORD=secure_password_here

# Webhook URLs (must be HTTPS in production)
PUBLIC_BASE_URL=https://your-domain.com
C2B_CONFIRMATION_URL=https://your-domain.com/webhook/c2b/confirmation
C2B_VALIDATION_URL=https://your-domain.com/webhook/c2b/validation

# Security
UI_TOKEN=generate_secure_random_token
```

### 3. Generate Secure Tokens

```bash
# Generate secure UI token
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Local Development Deployment

### Quick Start

```bash
# 1. Setup virtual environment
make setup

# 2. Verify setup
make verify

# 3. Start infrastructure
make infra-up

# 4. Wait for services to be ready (30 seconds)
sleep 30

# 5. Check service health
docker compose ps
curl http://localhost:5000/health

# 6. Run database migrations (if needed)
make transform

# 7. Start consuming messages
make ingest
```

### Manual Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start Docker services
docker compose up -d

# Check logs
docker compose logs -f webhook-receiver
docker compose logs -f kafka-consumer

# Stop services
docker compose down
```

### Testing Local Deployment

```bash
# Test webhook endpoint
curl -X POST http://localhost:5000/webhook/c2b/confirmation \
  -H "Content-Type: application/json" \
  -d '{
    "TransID": "TEST123",
    "TransAmount": "100",
    "MSISDN": "254712345678",
    "AccountReference": "TEST",
    "TransTime": "20260613120000"
  }'

# Check Grafana
open http://localhost:3000
# Login: admin / admin123
```

---

## Staging Deployment

### 1. Prepare Staging Environment

```bash
# SSH to staging server
ssh user@staging.your-domain.com

# Clone repository
git clone https://github.com/kipruto45/Real_Time_Transaction_Streaming-MPESA-.git
cd Real_Time_Transaction_Streaming-MPESA-

# Checkout specific version
git checkout v1.0.0
```

### 2. Configure Staging Environment

```bash
# Copy staging configuration
cp .env.staging .env

# Update with staging credentials
nano .env
```

**Staging-specific settings**:
```bash
DARAJA_ENVIRONMENT=sandbox
PUBLIC_BASE_URL=https://staging.your-domain.com
LOG_LEVEL=DEBUG
POSTGRES_HOST=staging-db.your-domain.com
```

### 3. Deploy to Staging

```bash
# Build Docker images
docker compose -f docker-compose.prod.yml build

# Start services
docker compose -f docker-compose.prod.yml up -d

# Run migrations
docker compose -f docker-compose.prod.yml run --rm dbt run

# Verify deployment
curl https://staging.your-domain.com/health
```

### 4. Staging Validation

```bash
# Run integration tests
make test-integration

# Run end-to-end tests
make test-e2e

# Load testing
make load-test DURATION=5 USERS=50

# Check logs
docker compose -f docker-compose.prod.yml logs -f --tail=100
```

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] All tests passing in staging
- [ ] Database backups configured
- [ ] SSL certificates installed
- [ ] Monitoring alerts configured
- [ ] Rollback plan documented
- [ ] Team notified of deployment
- [ ] Maintenance window scheduled (if needed)

### 1. Prepare Production Environment

```bash
# SSH to production server
ssh user@prod.your-domain.com

# Create deployment directory
sudo mkdir -p /opt/mpesa-analytics
sudo chown $USER:$USER /opt/mpesa-analytics
cd /opt/mpesa-analytics

# Clone repository
git clone https://github.com/kipruto45/Real_Time_Transaction_Streaming-MPESA-.git .
git checkout v1.0.0
```

### 2. Configure Production

```bash
# Copy production configuration
cp .env.production .env

# Update with production credentials
nano .env
```

**Production settings**:
```bash
DARAJA_ENVIRONMENT=production
PUBLIC_BASE_URL=https://api.your-domain.com
LOG_LEVEL=INFO
POSTGRES_HOST=prod-db.your-domain.com
RATE_LIMIT_PER_MIN=120

# Use AWS RDS
RDS_HOST=mpesa-prod.xxxxx.us-east-1.rds.amazonaws.com
RDS_PORT=5432
RDS_DB_NAME=mpesa_analytics
RDS_USERNAME=mpesa_app
AWS_REGION=us-east-1
```

### 3. SSL Certificate Setup

```bash
# Install Certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d api.your-domain.com

# Verify auto-renewal
sudo certbot renew --dry-run
```

### 4. Deploy to Production

```bash
# Build production images
docker compose -f docker-compose.prod.yml build --no-cache

# Start services with zero downtime
docker compose -f docker-compose.prod.yml up -d --remove-orphans

# Run database migrations
docker compose -f docker-compose.prod.yml run --rm dbt run

# Verify deployment
curl https://api.your-domain.com/health
```

### 5. Register Webhook URLs

```bash
# Register URLs with Daraja API
python scripts/register_daraja_urls.py

# Verify registration
python scripts/test_daraja_oauth.py
```

### 6. Production Validation

```bash
# Health check
curl https://api.your-domain.com/health

# Test webhook (use Daraja sandbox first)
python scripts/test_daraja_c2b.py

# Monitor logs
docker compose -f docker-compose.prod.yml logs -f webhook-receiver

# Check Grafana dashboards
open https://grafana.your-domain.com
```

---

## Docker Deployment

### Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  webhook-receiver:
    build:
      context: .
      dockerfile: Dockerfile.webhook
    restart: always
    ports:
      - "5000:5000"
    environment:
      - LOG_LEVEL=INFO
    env_file:
      - .env
    depends_on:
      - postgres
      - kafka
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G

  kafka-consumer:
    build:
      context: .
      dockerfile: Dockerfile.consumer
    restart: always
    env_file:
      - .env
    depends_on:
      - kafka
      - postgres
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

### Build and Push Images

```bash
# Build images
docker build -t mpesa-webhook:v1.0.0 -f Dockerfile.webhook .
docker build -t mpesa-consumer:v1.0.0 -f Dockerfile.consumer .

# Tag for registry
docker tag mpesa-webhook:v1.0.0 your-registry/mpesa-webhook:v1.0.0
docker tag mpesa-consumer:v1.0.0 your-registry/mpesa-consumer:v1.0.0

# Push to registry
docker push your-registry/mpesa-webhook:v1.0.0
docker push your-registry/mpesa-consumer:v1.0.0
```

---

## Kubernetes Deployment

### 1. Prepare Kubernetes Cluster

```bash
# Verify cluster access
kubectl cluster-info
kubectl get nodes

# Create namespace
kubectl create namespace mpesa-analytics

# Set default namespace
kubectl config set-context --current --namespace=mpesa-analytics
```

### 2. Create Secrets

```bash
# Create secret from .env file
kubectl create secret generic mpesa-secrets \
  --from-env-file=.env \
  --namespace=mpesa-analytics

# Verify secret
kubectl get secrets
```

### 3. Deploy to Kubernetes

```bash
# Apply configurations
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/secrets.yaml
kubectl apply -f kubernetes/persistent-volumes.yaml
kubectl apply -f kubernetes/services.yaml
kubectl apply -f kubernetes/webhook-deployment.yaml
kubectl apply -f kubernetes/consumer-deployment.yaml
kubectl apply -f kubernetes/processor-deployment.yaml

# Or use deployment script
./kubernetes/deploy.sh
```

### 4. Verify Deployment

```bash
# Check pods
kubectl get pods

# Check services
kubectl get services

# Check logs
kubectl logs -f deployment/webhook-receiver

# Port forward for testing
kubectl port-forward service/webhook-receiver 5000:5000
```

### 5. Configure Ingress

```bash
# Apply ingress configuration
kubectl apply -f kubernetes/ingress.yaml

# Verify ingress
kubectl get ingress

# Check external IP
kubectl get ingress mpesa-ingress -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

---

## Cloud Deployment

### AWS Deployment

#### 1. Setup Infrastructure with Terraform

```bash
cd terraform

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var-file="production.tfvars"

# Apply configuration
terraform apply -var-file="production.tfvars"

# Get outputs
terraform output
```

#### 2. Deploy Application

```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com

docker build -t mpesa-webhook .
docker tag mpesa-webhook:latest YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/mpesa-webhook:latest
docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/mpesa-webhook:latest

# Deploy to ECS
aws ecs update-service --cluster mpesa-cluster --service webhook-service --force-new-deployment
```

### GCP Deployment

#### 1. Setup GCP Project

```bash
# Set project
gcloud config set project mpesa-analytics

# Enable APIs
gcloud services enable compute.googleapis.com
gcloud services enable container.googleapis.com
gcloud services enable sqladmin.googleapis.com
```

#### 2. Deploy to Cloud Run

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/mpesa-analytics/webhook

# Deploy to Cloud Run
gcloud run deploy webhook-receiver \
  --image gcr.io/mpesa-analytics/webhook \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="$(cat .env | xargs)"
```

---

## Post-Deployment

### 1. Verify Deployment

```bash
# Health check
curl https://api.your-domain.com/health

# Test transaction
curl -X POST https://api.your-domain.com/webhook/c2b/confirmation \
  -H "Content-Type: application/json" \
  -d @examples/sample_transaction.json

# Check metrics
curl https://api.your-domain.com/metrics
```

### 2. Configure Monitoring

```bash
# Setup Grafana dashboards
make dashboards

# Configure alerts
kubectl apply -f monitoring/alerting-rules.yml

# Test alerts
python scripts/test_alerts.py
```

### 3. Setup Backups

```bash
# Configure automated backups
crontab -e

# Add backup job (daily at 2 AM)
0 2 * * * /opt/mpesa-analytics/scripts/backup_database.sh
```

### 4. Documentation

```bash
# Update deployment log
echo "$(date): Deployed v1.0.0 to production" >> deployment.log

# Notify team
# Send deployment notification via Slack/email
```

---

## Rollback Procedures

### Quick Rollback

```bash
# Rollback to previous version
docker compose -f docker-compose.prod.yml down
git checkout v0.9.0
docker compose -f docker-compose.prod.yml up -d

# Or use Kubernetes
kubectl rollout undo deployment/webhook-receiver
kubectl rollout undo deployment/kafka-consumer
```

### Database Rollback

```bash
# Restore from backup
./scripts/restore_database.sh backup_20260613.sql

# Verify restoration
psql -h localhost -U data_engineer -d mpesa_analytics -c "SELECT COUNT(*) FROM mpesa_transactions_raw;"
```

### Complete Rollback Procedure

1. **Stop new traffic**
   ```bash
   # Update load balancer to maintenance page
   kubectl scale deployment webhook-receiver --replicas=0
   ```

2. **Restore database**
   ```bash
   ./scripts/restore_database.sh latest
   ```

3. **Deploy previous version**
   ```bash
   git checkout v0.9.0
   docker compose -f docker-compose.prod.yml up -d
   ```

4. **Verify rollback**
   ```bash
   curl https://api.your-domain.com/health
   make test-integration
   ```

5. **Resume traffic**
   ```bash
   kubectl scale deployment webhook-receiver --replicas=3
   ```

---

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions.

## Support

- **Documentation**: https://docs.your-domain.com
- **Issues**: https://github.com/kipruto45/Real_Time_Transaction_Streaming-MPESA-/issues
- **Email**: support@your-domain.com
- **Slack**: #mpesa-analytics-support
