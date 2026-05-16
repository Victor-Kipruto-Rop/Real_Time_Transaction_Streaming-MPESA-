# Terraform Configuration for M-Pesa Real-Time Transaction Streaming Pipeline

Complete Infrastructure-as-Code (IaC) setup for deploying the M-Pesa streaming pipeline to Google Cloud Platform (GCP).

## 📋 Overview

This Terraform configuration creates and manages all cloud infrastructure required for the M-Pesa pipeline, including:

- **BigQuery** - Data warehouse (raw, staging, analytics layers)
- **Cloud SQL** - PostgreSQL database for application state
- **Pub/Sub** - Event streaming with dead-letter queue handling
- **Cloud Run** - Serverless webhook receiver and consumers
- **Cloud Storage** - Artifact Registry for Docker images
- **VPC & Networking** - Private network with Cloud NAT and Serverless VPC Connector
- **IAM & Service Accounts** - Least-privilege access control
- **Secret Manager** - Secure credential storage
- **Cloud Monitoring** - Observability and alerting
- **Cloud Logging** - Centralized logging with BigQuery export

## 🚀 Quick Start

### Prerequisites

1. **Google Cloud Project** - With billing enabled
2. **gcloud CLI** - Install and configure with `gcloud auth login`
3. **Terraform** - v1.0+ (`terraform version`)
4. **Environment Variables** - GCP project ID set: `export GOOGLE_CLOUD_PROJECT=your-project-id`

### Setup Steps

1. **Configure Variables**
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   vim terraform.tfvars
   ```

2. **Initialize Terraform**
   ```bash
   terraform init
   ```

3. **Plan Infrastructure**
   ```bash
   terraform plan -out=tfplan
   ```

4. **Apply Configuration**
   ```bash
   terraform apply tfplan
   ```

5. **Save Outputs**
   ```bash
   terraform output > deployment-outputs.json
   ```

## 📁 File Structure

```
terraform/
├── providers.tf           # GCP and provider configuration
├── variables.tf          # Input variable declarations
├── locals.tf             # Local values and naming conventions
├── main.tf              # Core infrastructure setup
├── bigquery.tf          # BigQuery data warehouse
├── cloud-sql.tf         # PostgreSQL database
├── vpc.tf               # VPC and networking
├── iam.tf               # Service accounts and IAM roles
├── pubsub.tf            # Pub/Sub topics and subscriptions
├── cloud-run.tf         # Cloud Run services
├── secrets.tf           # Secret Manager configuration
├── monitoring.tf        # Monitoring and alerting
├── backend.tf           # Terraform state backend
├── outputs.tf           # Output values
├── terraform.tfvars.example  # Example variables
└── README.md            # This file
```

## 🔧 Key Configuration Files

### `terraform.tfvars`
Primary configuration file. Copy from `terraform.tfvars.example` and customize:

```hcl
gcp_project_id = "your-project-id"
gcp_region     = "us-central1"
environment    = "dev"  # dev, staging, prod
alert_email    = "your-email@example.com"
```

### Environment-Specific Configurations

The setup supports three environments:

**Development (dev)**
- Smaller instance types
- Autoscaling disabled
- Public IP enabled for debugging
- 30-day data retention

**Staging (staging)**
- Medium instance types
- Autoscaling enabled (min=1, max=3)
- Private network only
- 90-day data retention

**Production (prod)**
- Large instance types with redundancy
- Aggressive autoscaling (min=2, max=20)
- Regional database with HA
- Full backup and recovery
- 365-day data retention

## 🔑 Important Outputs

After `terraform apply`, key endpoints are available via:

```bash
# Get webhook URL
terraform output webhook_endpoint

# Get Cloud SQL connection string
terraform output cloud_sql_info

# Get BigQuery dataset names
terraform output bigquery_info

# Get all outputs
terraform output
```

## 🗝️ Secret Management

### Initial Setup

Secrets are created but contain placeholder values. Update them:

```bash
# Daraja API Key
gcloud secrets versions add "mps-dev-daraja-api-key" --data-file=- <<< "YOUR_ACTUAL_KEY"

# Daraja API Secret
gcloud secrets versions add "mps-dev-daraja-api-secret" --data-file=- <<< "YOUR_ACTUAL_SECRET"

# Webhook Signing Key
gcloud secrets versions add "mps-dev-webhook-signing-key" --data-file=- <<< "YOUR_SIGNING_KEY"
```

### Access Control

Service accounts have least-privilege IAM roles:
- **webhook** - Can publish to Pub/Sub, read/write BigQuery, access Cloud SQL
- **consumer** - Can subscribe from Pub/Sub, write BigQuery, access Cloud SQL
- **producer** - Can publish to Pub/Sub, read secrets
- **dataflow** - Can subscribe Pub/Sub, write BigQuery
- **dbt** - Limited BigQuery create/update permissions

## 🐳 Docker Image Deployment

Build and push Docker images to Artifact Registry:

```bash
# Get image repository prefix
REPO=$(terraform output -raw artifact_registry_info | grep image_prefix)

# Build and push webhook
docker build -t ${REPO}/webhook:latest ./ingestion
docker push ${REPO}/webhook:latest

# Build and push consumer
docker build -t ${REPO}/consumer:latest ./streaming
docker push ${REPO}/consumer:latest

# Redeploy Cloud Run services
terraform apply -var='cloud_run_webhook_image=${REPO}/webhook:latest'
```

## 🌐 Network Architecture

### VPC Setup
- CIDR: `10.0.0.0/16`
- Subnet: `10.0.1.0/24`
- Cloud NAT: For outbound internet access
- Private Service Connection: For Cloud SQL

### Firewall Rules
- Internal traffic allowed within subnet
- Cloud SQL accessible only from VPC
- Cloud Run behind IAM authentication
- Pub/Sub webhooks use IAM as auth

### Serverless Connectivity
- VPC Connector: Enables Cloud Run → Cloud SQL communication
- Instance count: 2-10 (auto-scaled)

## 📊 BigQuery Schema

### Datasets
- **raw_mpesa_{env}** - Raw incoming transactions
- **staging_mpesa_{env}** - dbt staging models
- **analytics_mpesa_{env}** - Business-ready marts
- **archive_mpesa_{env}** - Historical logs and audit

### Tables
- `mpesa_raw_transactions` - Raw webhook data
- `stg_mpesa_transactions` - Cleansed transactions
- `mart_hourly_transaction_volumes` - Hourly aggregations
- `mart_county_transaction_heatmap` - Geographic heatmap

### Partitioning & Clustering
All tables partitioned by date for cost optimization
Clustered by transaction type, merchant code, status for query performance

## 📈 Monitoring & Alerting

### Configured Alerts
1. Cloud SQL CPU > 80%
2. Cloud SQL Storage > 80%
3. Cloud Run latency (P95) > 1s
4. Cloud Run error rate > 5%
5. Pub/Sub lag > 1000 messages
6. Webhook service down (uptime check)
7. High error rate in logs

### Dashboard
Grafana/Cloud Monitoring dashboard with 6 key panels:
- Transaction volume
- Latency metrics
- Error rates
- Pub/Sub lag
- Database performance
- BigQuery job status

### Log Export
Logs exported to BigQuery for long-term analysis and compliance

## 🔄 CI/CD Integration

### GitHub Actions (Optional)

```yaml
# .github/workflows/terraform.yml
terraform:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v2
    - uses: hashicorp/setup-terraform@v1
    - run: terraform init
    - run: terraform plan
    - run: terraform apply
```

### Cloud Build (Optional)

```yaml
# cloudbuild.yaml
steps:
  - name: gcr.io/cloud-builders/terraform
    args: ['init']
  - name: gcr.io/cloud-builders/terraform
    args: ['plan', '-out=tfplan']
  - name: gcr.io/cloud-builders/terraform
    args: ['apply', 'tfplan']
```

## 🚀 Deployment Guide

### Step-by-Step

1. **Prepare GCP Project**
   ```bash
   gcloud projects create mpesa-streaming --name="M-Pesa Streaming"
   gcloud config set project mpesa-streaming
   gcloud billing projects link mpesa-streaming --billing-account=BILLING_ID
   ```

2. **Enable Required APIs**
   ```bash
   gcloud services enable compute.googleapis.com container.googleapis.com \
     bigquery.googleapis.com sqladmin.googleapis.com run.googleapis.com \
     pubsub.googleapis.com dataflow.googleapis.com
   ```

3. **Configure Terraform**
   ```bash
   cd terraform
   cp terraform.tfvars.example terraform.tfvars
   vim terraform.tfvars  # Edit with your values
   ```

4. **Deploy Infrastructure**
   ```bash
   terraform init
   terraform validate
   terraform plan
   terraform apply
   ```

5. **Post-Deployment**
   ```bash
   # Update secrets
   bash scripts/setup-secrets.sh
   
   # Initialize database
   psql -h [CLOUD_SQL_IP] -U mpesa_app -d mpesa_dev < scripts/schema.sql
   
   # Deploy Docker images
   bash scripts/build-and-push-images.sh
   
   # Configure webhooks in Daraja
   # Update: https://console.safaricom.co.ke/
   ```

## 🔐 Security Best Practices

1. **Secrets** - Never commit secrets; use Secret Manager
2. **IAM** - Least-privilege service accounts
3. **Network** - Private Cloud SQL with VPC peering
4. **Encryption** - All data in transit (TLS) and at rest
5. **Audit Logging** - All admin and data access logged
6. **Database** - Backups enabled for prod, SSO for access
7. **Monitoring** - 24/7 alerting for security events

## 🧹 Cleanup

To destroy all infrastructure and avoid costs:

```bash
# View what will be deleted
terraform plan -destroy

# Destroy infrastructure
terraform destroy

# Remove Terraform state
rm -rf terraform.tfstate* .terraform/
```

⚠️ **WARNING:** This permanently deletes:
- All BigQuery datasets and tables
- Cloud SQL database
- Cloud Run services
- All persistent data

## 📖 Common Tasks

### Scale Cloud Run
```bash
terraform apply -var='cloud_run_max_instances=20'
```

### Update database tier
```bash
terraform apply -var='cloud_sql_instance_tier=db-n1-standard-1'
```

### Change region
```bash
terraform apply -var='gcp_region=europe-west1'
```

### Enable monitoring
```bash
terraform apply -var='enable_monitoring=true'
```

## 🐛 Troubleshooting

### Terraform Init Fails
```bash
rm -rf .terraform
terraform init
```

### Permission Denied Errors
```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

### Cloud SQL Connection Issues
```bash
gcloud sql instances describe mps-dev-postgres --region us-central1
gcloud sql instances patch mps-dev-postgres --require-ssl=false
```

### BigQuery Access Denied
```bash
gcloud projects get-iam-policy PROJECT_ID --flatten="bindings[].members" --format="value(bindings.role)"
```

## 📞 Support & Documentation

- **Terraform Docs**: https://registry.terraform.io/providers/hashicorp/google/latest/docs
- **GCP Terraform Provider**: https://cloud.google.com/docs/terraform
- **M-Pesa Integration**: https://developer.safaricom.co.ke/
- **BigQuery Docs**: https://cloud.google.com/bigquery/docs
- **Cloud Run Docs**: https://cloud.google.com/run/docs

## 📝 Version History

- **v1.0.0** - Initial infrastructure setup
  - BigQuery, Cloud SQL, Pub/Sub
  - Cloud Run, VPC, IAM
  - Monitoring and logging
  - Support for dev/staging/prod environments

## 🤝 Contributing

Improvements and fixes welcome! Please:
1. Test changes locally with `terraform plan`
2. Document any new variables in `variables.tf`
3. Update this README with changes

## ⚖️ License

This Terraform configuration is part of the M-Pesa Streaming Pipeline project.

---

**Last Updated:** May 2026  
**Status:** Production Ready  
**Maintainer:** Data Engineering Team
