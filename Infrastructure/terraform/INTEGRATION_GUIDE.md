# Terraform Integration Guide - M-Pesa Streaming Pipeline

## Overview

This guide explains how to use the Terraform infrastructure code with the existing M-Pesa streaming pipeline project.

## 🎯 Project Structure After Terraform

```
Real_Time_Transaction_Streaming/
├── terraform/                    # ← ALL INFRASTRUCTURE CODE
│   ├── providers.tf
│   ├── variables.tf
│   ├── locals.tf
│   ├── main.tf
│   ├── bigquery.tf
│   ├── cloud-sql.tf
│   ├── vpc.tf
│   ├── iam.tf
│   ├── pubsub.tf
│   ├── cloud-run.tf
│   ├── secrets.tf
│   ├── monitoring.tf
│   ├── backend.tf
│   ├── outputs.tf
│   ├── terraform.tfvars.example
│   ├── validate.sh
│   ├── setup.sh
│   ├── .gitignore
│   └── README.md
│
├── ingestion/                   # ← Application code
├── streaming/
├── dbt/
├── dags/
├── tests/
├── scripts/
├── docs/
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── requirements.txt
└── README.md
```

## 🚀 Quickstart - Deploy to GCP in 5 Minutes

```bash
# 1. Set up Terraform
cd terraform
bash setup.sh

# 2. Review and approve infrastructure plan
terraform plan

# 3. Deploy to GCP
terraform apply

# 4. Get endpoints
terraform output webhook_endpoint
terraform output bigquery_info
```

## 📊 Terraform Handles (What It Creates)

### Cloud Infrastructure ☁️
- ✅ Google Cloud Project setup
- ✅ BigQuery datasets (raw, staging, analytics, archive)
- ✅ Cloud SQL PostgreSQL database
- ✅ Pub/Sub topics & subscriptions
- ✅ Cloud Run services (webhook receiver)
- ✅ VPC network & firewalls
- ✅ Artifact Registry for Docker images
- ✅ Service accounts & IAM roles
- ✅ Secret Manager for credentials
- ✅ Cloud Monitoring & alerting
- ✅ Cloud Logging with BigQuery export

### What Your Application Code Handles 🐍
- User-written Python modules (ingestion, streaming, transformations)
- dbt models and transformations
- Airflow DAGs for orchestration
- Unit tests and integration tests
- Docker container images
- CI/CD pipelines

## 🔄 Deployment Workflow

### Local Development (docker-compose)
```bash
# Everything runs locally without Terraform
make infra-up
make run-all
make test-all
```

### Staging/Production (GCP with Terraform)
```bash
# 1. Prepare infrastructure
terraform plan -var-file=dev.tfvars
terraform apply -var-file=dev.tfvars

# 2. Build & deploy Docker images
docker build -t gcr.io/PROJECT/webhook ./ingestion
docker push gcr.io/PROJECT/webhook
# Cloud Run automatically pulls from Artifact Registry

# 3. Initialize database & dbt
psql -h [CLOUD_SQL_IP] -U mpesa_app < scripts/schema.sql
dbt run --profiles-dir=dbt --target=dev

# 4. Test pipeline
curl https://webhook-service-url/health
gcloud pubsub subscriptions pull transactions-sub --limit=5
```

## 🔐 Secrets Management

### Development (local)
```bash
# Store in .env (git-ignored)
DARAJA_API_KEY=xxx
DARAJA_API_SECRET=xxx
```

### Production (GCP Secret Manager via Terraform)
```bash
# Secrets created by Terraform but need manual values
gcloud secrets versions add "mps-dev-daraja-api-key" --data-file=- < api_key.txt

# Services access via:
# - environment variable injection
# - Secret Manager API
# - Service account permissions (IAM)
```

## 📈 Terraform-Managed vs Manual Configuration

### Automated by Terraform ✅
```
Infrastructure:
  - BigQuery schemas & tables
  - Cloud SQL instance & database
  - VPC & networking
  - Service accounts & IAM
  - Monitoring & alerting
  - Secret storage

Configuration:
  - Firewall rules
  - Network ACLs
  - Database backups
  - Autoscaling policies
```

### Managed by Application Code 🔧
```
Configuration:
  - dbt profiles & models
  - Airflow DAGs & schedules
  - Python application code
  - Docker images
  - Makefile targets
```

### Manual Post-Deployment 👤
```
Secrets:
  - Daraja API credentials
  - Webhook signing keys
  - OAuth tokens

Configuration:
  - Safaricom Daraja webhook URLs
  - Custom monitoring alerts
  - Email notification lists
```

## 🌍 Multi-Environment Support

### Development
```bash
# Run locally with docker-compose
make infra-up
# OR deploy to GCP dev environment
terraform apply -var-file=dev.tfvars
```

### Staging
```bash
terraform apply -var-file=staging.tfvars
# Runs in separate GCP environment
```

### Production
```bash
terraform apply -var-file=prod.tfvars
# Full redundancy, HA database, aggressive autoscaling
```

## 🔗 Integration Points

### Docker Containers
```yaml
# Terraform creates the infrastructure
# Your Dockerfile builds the image
# Cloud Run pulls from Artifact Registry
docker build -t ${REPO}/webhook:latest .
docker push ${REPO}/webhook:latest
# Terraform references the image in Cloud Run service
```

### Database Initialization
```bash
# Terraform creates the database
terraform output cloud_sql_info
# Your scripts/schema.sql initializes tables
psql -h [IP] -U [user] -d [db] < scripts/schema.sql
# dbt then runs transformations
dbt run
```

### Orchestration
```bash
# Terraform sets up infrastructure
# Airflow DAGs (in dags/) orchestrate the pipeline
# dags/mpesa_batch_dag.py triggers dbt transforms
# dags/mpesa_streaming_dag.py manages Kafka consumers
```

## 📝 Configuration Files Reference

### terraform.tfvars (Your Configuration)
```hcl
gcp_project_id = "my-project"
environment    = "dev"
alert_email    = "team@example.com"
# ... other values
```

### deployment-outputs.json (Terraform Output)
```json
{
  "webhook_endpoint": "https://webhook-service-url",
  "bigquery_info": {
    "raw_dataset": "raw_mpesa_dev",
    "staging_dataset": "staging_mpesa_dev"
  },
  "cloud_sql_info": {
    "instance_name": "mps-dev-postgres",
    "connection_name": "project:region:instance"
  }
}
```

### Environment Variables (Application)
```bash
# Set from Terraform outputs + other sources
GCP_PROJECT_ID=$(terraform output -raw project_info | jq -r '.project_id')
PUBSUB_TOPIC=$(terraform output -raw pubsub_info | jq -r '.transactions_topic')
DATABASE_URL=$(gcloud secrets versions access latest --secret="connection-string")
```

## 🧪 Testing Infrastructure

```bash
# Validate Terraform
terraform validate
terraform fmt -check
tfsec .

# Plan changes
terraform plan -out=tfplan

# Test infrastructure
gcloud compute networks list
gcloud sql instances list
bq ls
gcloud run services list

# Test connectivity
gcloud sql connect mps-dev-postgres --user=postgres
curl https://webhook-url/health
gcloud pubsub subscriptions pull test-sub --limit=1
```

## 🐛 Troubleshooting

### Terraform Issues
```bash
# Debug provider
TF_LOG=DEBUG terraform plan

# Clear state issues
terraform refresh

# Validate syntax
terraform fmt -recursive .
terraform validate
```

### Connectivity Issues
```bash
# Test Cloud Run
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" https://webhook-url/health

# Test Cloud SQL
gcloud sql connect instance-name --user=user

# Test Pub/Sub
gcloud pubsub topics list
gcloud pubsub subscriptions pull sub-name --limit=1
```

### Permission Issues
```bash
# Check service account roles
gcloud projects get-iam-policy PROJECT_ID --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:*"

# Grant missing roles
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member=serviceAccount:account@project.iam.gserviceaccount.com \
  --role=roles/bigquery.editor
```

## 📋 Checklist - From Code to Production

- [ ] **Terraform configured** (terraform.tfvars created)
- [ ] **Infrastructure deployed** (terraform apply)
- [ ] **Secrets updated** (gcloud secrets versions add)
- [ ] **Docker images built** (docker build & push)
- [ ] **Database initialized** (schema.sql executed)
- [ ] **dbt models deployed** (dbt run)
- [ ] **Webhooks configured** (Safaricom Daraja)
- [ ] **Tests passing** (make test-all)
- [ ] **Monitoring active** (alerts configured)
- [ ] **Logs flowing** (BigQuery exports working)
- [ ] **Performance verified** (load tests run)
- [ ] **Security reviewed** (IAM, secrets, networking)

## 📞 Support Resources

- **Terraform Docs**: https://www.terraform.io/docs
- **GCP Provider**: https://registry.terraform.io/providers/hashicorp/google/latest/docs
- **GCP Project Setup**: https://cloud.google.com/docs/setup
- **Cloud Run**: https://cloud.google.com/run/docs/quickstarts/build-and-deploy
- **BigQuery**: https://cloud.google.com/bigquery/docs/quickstarts
- **Daraja API**: https://developer.safaricom.co.ke/

## 🔄 CI/CD Integration

### GitHub Actions Example
```yaml
name: Deploy Infrastructure
on: [push]
jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: hashicorp/setup-terraform@v1
      - run: terraform init
      - run: terraform validate
      - run: terraform plan
      - run: terraform apply
```

### Cloud Build Example
```yaml
steps:
  - name: Initialize
    args: ['terraform', 'init']
  - name: Validate
    args: ['terraform', 'validate']
  - name: Plan
    args: ['terraform', 'plan', '-out=tfplan']
  - name: Apply
    args: ['terraform', 'apply', 'tfplan']
```

## 📊 Cost Management

### View Costs
```bash
# Get billing information
gcloud billing accounts list
gcloud billing projects describe PROJECT_ID

# Monitor usage
gcloud compute project-info describe --project=PROJECT_ID
```

### Cost Optimization
- Use `terraform.tfvars` to set smaller instances for dev
- Enable autoscaling to scale down during low traffic
- Set retention policies on BigQuery/logs
- Use Cloud NAT for outbound traffic instead of public IPs
- Archive old data to Cloud Storage

---

**Status:** Ready for Production  
**Last Updated:** May 2026  
**Version:** 1.0.0
