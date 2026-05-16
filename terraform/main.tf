# Main Terraform configuration for M-Pesa Real-Time Transaction Streaming Pipeline
# This file orchestrates all infrastructure resources

# Enable required Google Cloud APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "compute.googleapis.com",
    "container.googleapis.com",
    "bigquery.googleapis.com",
    "sqladmin.googleapis.com",
    "run.googleapis.com",
    "pubsub.googleapis.com",
    "dataflow.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudlogging.googleapis.com",
    "monitoring.googleapis.com",
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
    "servicenetworking.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "vpcaccess.googleapis.com",
  ])

  service            = each.value
  disable_on_destroy = false
}

# Create a random suffix for globally unique resource names
resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

# Terraform state bucket (if not using Terraform Cloud)
resource "google_storage_bucket" "terraform_state" {
  count    = var.terraform_cloud_org == "" ? 1 : 0
  name     = "${var.gcp_project_id}-tfstate-${random_string.bucket_suffix.result}"
  location = var.gcp_region

  uniform_bucket_level_access = true
  versioning {
    enabled = true
  }

  labels = local.common_labels

  depends_on = [google_project_service.required_apis]
}

# Service account for Terraform (for OIDC federation)
resource "google_service_account" "terraform" {
  account_id   = "${local.resource_prefix}-terraform"
  display_name = "Terraform Service Account for M-Pesa Streaming"
  description  = "Service account used by Terraform to manage infrastructure"

  depends_on = [google_project_service.required_apis]
}

# Grant Terraform service account necessary permissions
resource "google_project_iam_member" "terraform_editor" {
  project = var.gcp_project_id
  role    = "roles/editor"
  member  = "serviceAccount:${google_service_account.terraform.email}"

  depends_on = [google_project_service.required_apis]
}

# Enable audit logging
resource "google_project_iam_audit_config" "project" {
  project = var.gcp_project_id
  service = "allServices"

  audit_log_config {
    log_type = "ADMIN_WRITE"
  }

  audit_log_config {
    log_type = "DATA_READ"
  }

  audit_log_config {
    log_type = "DATA_WRITE"
  }

  depends_on = [google_project_service.required_apis]
}

# Log sink for exporting logs to BigQuery for analysis
resource "google_logging_project_sink" "bigquery_sink" {
  count            = var.enable_logging ? 1 : 0
  name             = "${local.resource_prefix}-bigquery-sink"
  destination      = "bigquery.googleapis.com/projects/${var.gcp_project_id}/datasets/${google_bigquery_dataset.archive.dataset_id}"
  filter           = "resource.type=\"cloud_run_revision\" OR resource.type=\"cloudsql_database\" OR resource.type=\"gke_container\""
  unique_writer_identity = true

  depends_on = [google_project_service.required_apis]
}

# Grant the logging service account permission to write to BigQuery
resource "google_bigquery_dataset_iam_member" "logging_sink" {
  count      = var.enable_logging ? 1 : 0
  dataset_id = google_bigquery_dataset.archive.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_logging_project_sink.bigquery_sink[0].writer_identity

  depends_on = [google_project_service.required_apis]
}

# Health check for monitoring resources
resource "google_compute_health_check" "mps_health_check" {
  name   = "${local.resource_prefix}-health-check"
  timeout_sec = 5
  check_interval_sec = 10

  http_health_check {
    port = "8080"
    request_path = "/health"
  }

  depends_on = [google_project_service.required_apis]
}

# Notification channels for alerts
resource "google_monitoring_notification_channel" "email" {
  display_name = "M-Pesa Email Notification"
  type         = "email"
  
  labels = {
    email_address = var.alert_email
  }

  enabled = true
}

# Outputs the configuration summary
output "infrastructure_status" {
  description = "Infrastructure deployment status"
  value = {
    project_id                = var.gcp_project_id
    environment               = var.environment
    region                    = var.gcp_region
    terraform_state_bucket   = try(google_storage_bucket.terraform_state[0].name, "Using Terraform Cloud")
    notification_channel_id   = google_monitoring_notification_channel.email.id
    apis_enabled             = length(google_project_service.required_apis) > 0 ? true : false
  }
}
