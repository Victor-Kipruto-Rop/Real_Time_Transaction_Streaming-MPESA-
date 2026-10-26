### GCP Configuration Variables
variable "gcp_project_id" {
  description = "GCP Project ID"
  type        = string
  validation {
    condition     = length(var.gcp_project_id) > 0
    error_message = "GCP Project ID must not be empty"
  }
}

variable "gcp_region" {
  description = "GCP Region for resources"
  type        = string
  default     = "us-central1"
  validation {
    condition     = contains(["us-central1", "us-east1", "us-west1", "europe-west1", "asia-east1"], var.gcp_region)
    error_message = "GCP Region must be a valid region"
  }
}

variable "gcp_zones" {
  description = "GCP Zones for zonal resources"
  type        = list(string)
  default     = ["us-central1-a", "us-central1-b", "us-central1-c"]
}

### Environment Configuration
variable "environment" {
  description = "Environment name (dev/staging/prod)"
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod"
  }
}

variable "team_label" {
  description = "Team responsible for this project"
  type        = string
  default     = "data-engineering"
}

### Terraform Configuration
variable "terraform_cloud_org" {
  description = "Terraform Cloud Organization (leave empty if not using Terraform Cloud)"
  type        = string
  default     = ""
}

variable "terraform_workspace" {
  description = "Terraform Cloud Workspace name"
  type        = string
  default     = "mpesa-streaming"
}

### Project Names
variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "mpesa-streaming"
}

variable "project_short_name" {
  description = "Short project name for brevity"
  type        = string
  default     = "mps"
}

### BigQuery Configuration
variable "bigquery_datasets" {
  description = "BigQuery datasets to create"
  type = object({
    raw        = string
    staging    = string
    analytics  = string
    archive    = string
  })
  default = {
    raw       = "raw_mpesa"
    staging   = "staging_mpesa"
    analytics = "analytics_mpesa"
    archive   = "archive_mpesa"
  }
}

variable "bigquery_tables_expiration_ms" {
  description = "Default expiration time in milliseconds for BigQuery tables (30 days)"
  type        = number
  default     = 2592000000  # 30 days
}

variable "bigquery_dataset_location" {
  description = "BigQuery dataset location"
  type        = string
  default     = "US"
  validation {
    condition     = contains(["US", "EU", "us-central1", "europe-west1", "asia-southeast1"], var.bigquery_dataset_location)
    error_message = "BigQuery location must be a valid location"
  }
}

### Cloud SQL Configuration
variable "cloud_sql_instance_tier" {
  description = "Cloud SQL instance machine tier"
  type        = string
  default     = "db-f1-micro"
}

variable "cloud_sql_backup_location" {
  description = "Cloud SQL backup location"
  type        = string
  default     = "us-central1"
}

variable "cloud_sql_database_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "POSTGRES_15"
}

variable "cloud_sql_root_password" {
  description = "Cloud SQL root password (stored in Secret Manager)"
  type        = string
  sensitive   = true
}

variable "cloud_sql_app_user_password" {
  description = "Cloud SQL application user password (stored in Secret Manager)"
  type        = string
  sensitive   = true
}

### Pub/Sub Configuration
variable "pubsub_topics" {
  description = "Pub/Sub topics to create"
  type = object({
    transactions     = string
    enriched         = string
    dead_letter      = string
  })
  default = {
    transactions     = "mpesa-transactions"
    enriched         = "mpesa-enriched"
    dead_letter      = "mpesa-dlq"
  }
}

variable "pubsub_subscription_retention_days" {
  description = "Pub/Sub message retention in days"
  type        = number
  default     = 7
}

### Cloud Run Configuration
variable "cloud_run_webhook_memory" {
  description = "Cloud Run webhook receiver memory allocation"
  type        = string
  default     = "512Mi"
}

variable "cloud_run_webhook_cpu" {
  description = "Cloud Run webhook receiver CPU allocation"
  type        = string
  default     = "1"
}

variable "cloud_run_webhook_timeout" {
  description = "Cloud Run webhook timeout in seconds"
  type        = number
  default     = 60
}

variable "cloud_run_webhook_concurrent_requests" {
  description = "Cloud Run webhook concurrent requests"
  type        = number
  default     = 100
}

variable "cloud_run_min_instances" {
  description = "Minimum instances for Cloud Run"
  type        = number
  default     = 1
}

variable "cloud_run_max_instances" {
  description = "Maximum instances for Cloud Run"
  type        = number
  default     = 10
}

variable "cloud_run_webhook_env_vars" {
  description = "Environment variables for Cloud Run webhook"
  type        = map(string)
  default     = {}
  sensitive   = true
}

### Dataflow (Flink) Configuration
variable "dataflow_zone" {
  description = "Zone for Dataflow jobs"
  type        = string
  default     = "us-central1-a"
}

variable "dataflow_worker_num_threads" {
  description = "Number of worker threads for Dataflow"
  type        = number
  default     = 2
}

variable "dataflow_autoscaling_algorithm" {
  description = "Autoscaling algorithm (THROUGHPUT_BASED or NONE)"
  type        = string
  default     = "THROUGHPUT_BASED"
}

### VPC Configuration
variable "enable_private_connectivity" {
  description = "Enable private connectivity for Cloud SQL"
  type        = bool
  default     = true
}

variable "vpc_cidr_range" {
  description = "VPC CIDR range"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_cidr_range" {
  description = "Subnet CIDR range"
  type        = string
  default     = "10.0.1.0/24"
}

### Monitoring & Logging
variable "enable_monitoring" {
  description = "Enable Cloud Monitoring"
  type        = bool
  default     = true
}

variable "enable_logging" {
  description = "Enable Cloud Logging"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "Cloud Logging retention in days"
  type        = number
  default     = 30
}

### Secret Manager
variable "secrets_to_create" {
  description = "Secrets to create in Secret Manager"
  type        = list(string)
  default = [
    "daraja-api-key",
    "daraja-api-secret",
    "webhook-signing-key",
    "db-root-password",
    "db-app-password",
    "gcp-service-account-key"
  ]
}

### Artifact Registry
variable "artifact_registry_repository_id" {
  description = "Artifact Registry repository ID"
  type        = string
  default     = "mpesa-docker"
}

variable "artifact_registry_repository_format" {
  description = "Artifact Registry repository format"
  type        = string
  default     = "DOCKER"
}

### Cloud Build Configuration
variable "enable_cloud_build" {
  description = "Enable Cloud Build for CI/CD"
  type        = bool
  default     = true
}

variable "cloud_build_github_owner" {
  description = "GitHub repository owner"
  type        = string
  default     = ""
}

variable "cloud_build_github_repo" {
  description = "GitHub repository name"
  type        = string
  default     = ""
}

### Scaling Configuration
variable "scaling_config" {
  description = "Scaling configuration for resources"
  type = object({
    enable_autoscaling = bool
    min_replicas      = number
    max_replicas      = number
  })
  default = {
    enable_autoscaling = true
    min_replicas      = 1
    max_replicas      = 3
  }
}

### Tags & Labels
variable "additional_labels" {
  description = "Additional labels to apply to all resources"
  type        = map(string)
  default     = {}
}

### Cost Control
variable "enable_budget_alerts" {
  description = "Enable budget alerts"
  type        = bool
  default     = true
}

variable "budget_monthly_limit_usd" {
  description = "Monthly budget limit in USD"
  type        = number
  default     = 500
}

variable "budget_alert_threshold_percentage" {
  description = "Percentage of budget threshold for alerts"
  type        = list(number)
  default     = [50, 75, 100]
}

variable "alert_email" {
  description = "Email address for budget alerts"
  type        = string
}
