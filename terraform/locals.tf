locals {
  # Resource naming conventions
  resource_prefix = "${var.project_short_name}-${var.environment}"
  
  # Common labels for all resources
  common_labels = merge(
    {
      project     = var.project_name
      environment = var.environment
      managed_by  = "terraform"
      created_at  = timestamp()
    },
    var.additional_labels
  )

  # BigQuery dataset names with environment suffix
  bigquery_raw_dataset      = "${var.bigquery_datasets.raw}_${var.environment}"
  bigquery_staging_dataset  = "${var.bigquery_datasets.staging}_${var.environment}"
  bigquery_analytics_dataset = "${var.bigquery_datasets.analytics}_${var.environment}"
  bigquery_archive_dataset   = "${var.bigquery_datasets.archive}_${var.environment}"

  # Database names
  cloud_sql_instance_name    = "${local.resource_prefix}-postgres"
  cloud_sql_database_name    = "mpesa_${replace(var.environment, "-", "_")}"

  # Service account names
  webhook_service_account_name = "${local.resource_prefix}-webhook"
  consumer_service_account_name = "${local.resource_prefix}-consumer"
  producer_service_account_name = "${local.resource_prefix}-producer"
  dataflow_service_account_name = "${local.resource_prefix}-dataflow"

  # VPC names
  vpc_name           = "${local.resource_prefix}-vpc"
  subnet_name        = "${local.resource_prefix}-subnet"
  cloud_router_name  = "${local.resource_prefix}-router"
  nat_gateway_name   = "${local.resource_prefix}-nat"

  # Pub/Sub names with environment suffix
  pubsub_transactions_topic = "${var.pubsub_topics.transactions}-${var.environment}"
  pubsub_enriched_topic     = "${var.pubsub_topics.enriched}-${var.environment}"
  pubsub_dlq_topic          = "${var.pubsub_topics.dead_letter}-${var.environment}"

  # Cloud Run service names
  webhook_service_name = "${local.resource_prefix}-webhook"
  consumer_service_name = "${local.resource_prefix}-consumer"

  # Cloud SQL database users
  db_root_user = "postgres"
  db_app_user  = "mpesa_app"

  # Artifact Registry repository name
  artifact_registry_repo_name = "${local.resource_prefix}-${var.artifact_registry_repository_id}"

  # Secret Manager secret names
  secret_names = {
    daraja_api_key        = "${local.resource_prefix}-daraja-api-key"
    daraja_api_secret     = "${local.resource_prefix}-daraja-api-secret"
    webhook_signing_key   = "${local.resource_prefix}-webhook-signing-key"
    db_root_password      = "${local.resource_prefix}-db-root-password"
    db_app_password       = "${local.resource_prefix}-db-app-password"
    service_account_key   = "${local.resource_prefix}-gcp-service-account-key"
  }

  # Monitoring
  alert_policy_display_name = "${var.project_name} - ${var.environment}"
  
  # Environment-specific configurations
  is_production = var.environment == "prod"
  is_staging    = var.environment == "staging"
  is_dev        = var.environment == "dev"

  # Database backup configuration
  backup_config = {
    enabled             = local.is_production || local.is_staging ? true : false
    backup_location     = var.cloud_sql_backup_location
    transaction_log_retention_days = local.is_production ? 7 : 3
  }

  # Retention policies
  retention_policies = {
    logs           = var.log_retention_days
    cloud_sql_logs = local.is_production ? 90 : 30
    bigquery_data  = local.is_production ? 365 : 90
  }

  # Cost optimization tags
  cost_center = "data-engineering"
  cost_optimization = {
    auto_scaling_enabled = var.scaling_config.enable_autoscaling
    spot_enabled        = !local.is_production
    commitment_plan     = local.is_production ? "monthly" : "on-demand"
  }
}
