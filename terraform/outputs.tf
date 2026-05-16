# Terraform Outputs - Critical infrastructure endpoints and references

output "project_info" {
  description = "Basic project information"
  value = {
    project_id      = var.gcp_project_id
    project_name    = var.project_name
    environment     = var.environment
    region          = var.gcp_region
    zones           = var.gcp_zones
  }
}

output "webhook_endpoint" {
  description = "Cloud Run webhook endpoint URL"
  value       = google_cloud_run_service.webhook.status[0].url
}

output "webhook_service_account" {
  description = "Webhook service account email"
  value       = google_service_account.webhook.email
  sensitive   = true
}

output "bigquery_info" {
  description = "BigQuery dataset and table information"
  value = {
    raw_dataset        = google_bigquery_dataset.raw.dataset_id
    staging_dataset    = google_bigquery_dataset.staging.dataset_id
    analytics_dataset  = google_bigquery_dataset.analytics.dataset_id
    archive_dataset    = google_bigquery_dataset.archive.dataset_id
    raw_table          = "${google_bigquery_dataset.raw.dataset_id}.${google_bigquery_table.raw_transactions.table_id}"
    staging_table      = "${google_bigquery_dataset.staging.dataset_id}.${google_bigquery_table.staging_transactions.table_id}"
    hourly_volumes_table = "${google_bigquery_dataset.analytics.dataset_id}.${google_bigquery_table.analytics_hourly_volumes.table_id}"
    county_heatmap_table = "${google_bigquery_dataset.analytics.dataset_id}.${google_bigquery_table.analytics_county_heatmap.table_id}"
  }
}

output "cloud_sql_info" {
  description = "Cloud SQL instance information"
  value = {
    instance_name     = google_sql_database_instance.postgres.name
    instance_address  = google_sql_database_instance.postgres.private_ip_address
    public_ip         = try(google_sql_database_instance.postgres.public_ip_address, "N/A")
    database_name     = google_sql_database.mpesa.name
    connection_name   = google_sql_database_instance.postgres.connection_name
    app_user          = google_sql_user.app.name
    region            = var.gcp_region
  }
  sensitive = true
}

output "pubsub_info" {
  description = "Pub/Sub topics and subscriptions"
  value = {
    transactions_topic      = google_pubsub_topic.transactions.name
    enriched_topic          = google_pubsub_topic.enriched.name
    dead_letter_topic       = google_pubsub_topic.dead_letter.name
    transactions_sub        = google_pubsub_subscription.transactions.name
    enriched_sub            = google_pubsub_subscription.enriched.name
    dead_letter_sub         = google_pubsub_subscription.dead_letter.name
  }
}

output "vpc_info" {
  description = "VPC and networking information"
  value = {
    vpc_name               = google_compute_network.vpc.name
    subnet_name            = google_compute_subnetwork.subnet.name
    subnet_cidr            = google_compute_subnetwork.subnet.ip_cidr_range
    vpc_connector_name     = google_vpc_access_connector.connector.name
    static_ip              = try(google_compute_address.static[0].address, "N/A")
  }
}

output "service_accounts_info" {
  description = "Service accounts for different components"
  value = {
    webhook_sa    = google_service_account.webhook.email
    consumer_sa   = google_service_account.consumer.email
    producer_sa   = google_service_account.producer.email
    dataflow_sa   = google_service_account.dataflow.email
    dbt_sa        = try(google_service_account.dbt[0].email, "N/A")
    cloud_build_sa = try(google_service_account.cloud_build[0].email, "N/A")
  }
}

output "secrets_info" {
  description = "Secret Manager secret references"
  value = {
    daraja_api_key         = google_secret_manager_secret.daraja_api_key.id
    daraja_api_secret      = google_secret_manager_secret.daraja_api_secret.id
    webhook_signing_key    = google_secret_manager_secret.webhook_signing_key.id
    db_root_password       = google_secret_manager_secret.db_root_password.id
    db_app_password        = google_secret_manager_secret.db_app_password.id
    db_connection_string   = google_secret_manager_secret.db_connection_string.id
  }
  sensitive = true
}

output "artifact_registry_info" {
  description = "Artifact Registry repository information"
  value = {
    repository_name = google_artifact_registry_repository.docker.repository_id
    repository_url  = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${google_artifact_registry_repository.docker.repository_id}"
    image_prefix    = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${google_artifact_registry_repository.docker.repository_id}"
  }
}

output "monitoring_info" {
  description = "Monitoring and alerting setup"
  value = {
    notification_channel_id = google_monitoring_notification_channel.email.id
    alert_email             = var.alert_email
    monitoring_enabled      = var.enable_monitoring
    logging_enabled         = var.enable_logging
    dashboard_name          = try(google_monitoring_dashboard.mpesa[0].id, "N/A")
  }
}

output "deployment_checklist" {
  description = "Next steps for deployment"
  value = <<EOT
=== M-Pesa Streaming Pipeline - Deployment Checklist ===

1. SECRETS TO UPDATE (in Secret Manager):
   - ${google_secret_manager_secret.daraja_api_key.id}
   - ${google_secret_manager_secret.daraja_api_secret.id}
   - ${google_secret_manager_secret.webhook_signing_key.id}

2. DOCKER IMAGES TO BUILD & PUSH:
   - docker build -t ${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${google_artifact_registry_repository.docker.repository_id}/webhook:latest ./ingestion
   - docker build -t ${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${google_artifact_registry_repository.docker.repository_id}/consumer:latest ./streaming
   - docker push ${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${google_artifact_registry_repository.docker.repository_id}/*

3. DATABASE SETUP:
   - Connect to ${google_sql_database_instance.postgres.connection_name}
   - Initialize schema: psql -h ${google_sql_database_instance.postgres.private_ip_address} -U ${google_sql_user.app.name} -d ${google_sql_database.mpesa.name} < scripts/schema.sql

4. DBT CONFIGURATION:
   - Update dbt/profiles.yml with BigQuery project: ${var.gcp_project_id}
   - Run: dbt debug
   - Run: dbt seed
   - Run: dbt run

5. WEBHOOKS CONFIGURATION:
   - Update Safaricom Daraja callbacks to: ${google_cloud_run_service.webhook.status[0].url}/webhook

6. MONITORING:
   - Verify alerts: gcloud alpha monitoring policies list
   - Check logs: gcloud logging read "resource.type=cloud_run_revision"

7. VERIFICATION:
   - Test webhook: curl -X POST ${google_cloud_run_service.webhook.status[0].url}/health
   - Check BigQuery: gcloud bq ls ${google_bigquery_dataset.raw.dataset_id}
   - Verify Pub/Sub: gcloud pubsub subscriptions pull ${google_pubsub_subscription.transactions.name}

8. PRODUCTION CHECKLIST:
   - [ ] All secrets updated in Secret Manager
   - [ ] Docker images built and deployed
   - [ ] Database schema initialized
   - [ ] dbt models compiled and tested
   - [ ] Webhook URLs configured in Daraja
   - [ ] Monitoring alerts tested
   - [ ] Backups configured
   - [ ] IAM roles verified
EOT
}

output "cost_estimate" {
  description = "Estimated monthly costs (this is indicative only)"
  value = <<EOT
=== Estimated Monthly Costs (${var.environment} environment) ===

Cloud Run (Webhook):          $10-50/month
Cloud SQL (PostgreSQL):       $30-100/month
BigQuery (Analytics):         $50-200/month
Pub/Sub (Topics/Subs):        $20-50/month
Cloud Storage (logs):         $5-10/month
VPC Connector:                $10/month
Networking:                   $5-20/month
───────────────────────────
TOTAL ESTIMATE:               $130-430/month

Notes:
- Costs vary based on data volume and query complexity
- Production environment will have higher costs due to redundancy
- Set up budget alerts at: ${var.budget_monthly_limit_usd} USD
EOT
}

output "useful_commands" {
  description = "Useful gcloud commands for management"
  value = <<EOT
=== Useful gcloud Commands ===

# View webhook logs
gcloud logs read --project=${var.gcp_project_id} --service=cloud_run_revision --service-name=${google_cloud_run_service.webhook.name} --limit=50

# Monitor Cloud Run
gcloud run services describe ${google_cloud_run_service.webhook.name} --platform=managed --region=${var.gcp_region}

# Check Pub/Sub messages
gcloud pubsub subscriptions pull ${google_pubsub_subscription.transactions.name} --limit=10

# Query BigQuery
bq query --use_legacy_sql=false 'SELECT * FROM `${var.gcp_project_id}.${google_bigquery_dataset.raw.dataset_id}.${google_bigquery_table.raw_transactions.table_id}` LIMIT 10'

# Tail logs
gcloud alpha logging tail --project=${var.gcp_project_id} "resource.type=cloud_run_revision AND resource.labels.service_name=${google_cloud_run_service.webhook.name}"

# Deploy Cloud Run service
gcloud run deploy ${google_cloud_run_service.webhook.name} \
  --image=${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${google_artifact_registry_repository.docker.repository_id}/webhook:latest \
  --region=${var.gcp_region} \
  --service-account=${google_service_account.webhook.email}

# Connect to Cloud SQL
gcloud sql connect ${google_sql_database_instance.postgres.name} --user=${google_sql_user.app.name} --database=${google_sql_database.mpesa.name}

# View monitoring dashboard
gcloud monitoring dashboards list
EOT
}
