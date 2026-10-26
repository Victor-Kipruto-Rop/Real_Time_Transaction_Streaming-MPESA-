# IAM and Service Accounts Configuration

# Webhook Receiver Service Account
resource "google_service_account" "webhook" {
  account_id   = local.webhook_service_account_name
  display_name = "M-Pesa Webhook Receiver Service Account"
  description  = "Service account for webhook receiver (Cloud Run)"

  depends_on = [google_project_service.required_apis]
}

# Webhook roles
resource "google_project_iam_member" "webhook_pubsub_publisher" {
  project = var.gcp_project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.webhook.email}"
}

resource "google_project_iam_member" "webhook_bigquery_editor" {
  project = var.gcp_project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.webhook.email}"
}

resource "google_project_iam_member" "webhook_cloudsql_client" {
  project = var.gcp_project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.webhook.email}"
}

resource "google_project_iam_member" "webhook_secret_accessor" {
  project = var.gcp_project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.webhook.email}"
}

resource "google_project_iam_member" "webhook_logging" {
  project = var.gcp_project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.webhook.email}"
}

# Consumer Service Account
resource "google_service_account" "consumer" {
  account_id   = local.consumer_service_account_name
  display_name = "M-Pesa Consumer Service Account"
  description  = "Service account for Kafka/Pub/Sub consumer"

  depends_on = [google_project_service.required_apis]
}

# Consumer roles
resource "google_project_iam_member" "consumer_pubsub_subscriber" {
  project = var.gcp_project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.consumer.email}"
}

resource "google_project_iam_member" "consumer_bigquery_editor" {
  project = var.gcp_project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.consumer.email}"
}

resource "google_project_iam_member" "consumer_bigquery_job_user" {
  project = var.gcp_project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.consumer.email}"
}

resource "google_project_iam_member" "consumer_cloudsql_client" {
  project = var.gcp_project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.consumer.email}"
}

resource "google_project_iam_member" "consumer_secret_accessor" {
  project = var.gcp_project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.consumer.email}"
}

resource "google_project_iam_member" "consumer_logging" {
  project = var.gcp_project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.consumer.email}"
}

resource "google_project_iam_member" "consumer_monitoring_metric_writer" {
  project = var.gcp_project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.consumer.email}"
}

# Producer Service Account
resource "google_service_account" "producer" {
  account_id   = local.producer_service_account_name
  display_name = "M-Pesa Producer Service Account"
  description  = "Service account for Kafka producer / data ingestion"

  depends_on = [google_project_service.required_apis]
}

# Producer roles
resource "google_project_iam_member" "producer_pubsub_publisher" {
  project = var.gcp_project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.producer.email}"
}

resource "google_project_iam_member" "producer_bigquery_editor" {
  project = var.gcp_project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.producer.email}"
}

resource "google_project_iam_member" "producer_secret_accessor" {
  project = var.gcp_project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.producer.email}"
}

resource "google_project_iam_member" "producer_logging" {
  project = var.gcp_project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.producer.email}"
}

# Dataflow Service Account
resource "google_service_account" "dataflow" {
  account_id   = local.dataflow_service_account_name
  display_name = "M-Pesa Dataflow Service Account"
  description  = "Service account for Apache Flink / Dataflow jobs"

  depends_on = [google_project_service.required_apis]
}

# Dataflow roles
resource "google_project_iam_member" "dataflow_worker" {
  project = var.gcp_project_id
  role    = "roles/dataflow.worker"
  member  = "serviceAccount:${google_service_account.dataflow.email}"
}

resource "google_project_iam_member" "dataflow_admin" {
  project = var.gcp_project_id
  role    = "roles/dataflow.admin"
  member  = "serviceAccount:${google_service_account.dataflow.email}"
}

resource "google_project_iam_member" "dataflow_pubsub_subscriber" {
  project = var.gcp_project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.dataflow.email}"
}

resource "google_project_iam_member" "dataflow_bigquery_editor" {
  project = var.gcp_project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.dataflow.email}"
}

resource "google_project_iam_member" "dataflow_bigquery_job_user" {
  project = var.gcp_project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.dataflow.email}"
}

resource "google_project_iam_member" "dataflow_storage_object_admin" {
  project = var.gcp_project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.dataflow.email}"
}

resource "google_project_iam_member" "dataflow_logging" {
  project = var.gcp_project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.dataflow.email}"
}

# Cloud Run Invoker for webhook
resource "google_service_account_iam_member" "webhook_run_invoker" {
  service_account_id = google_service_account.webhook.name
  role               = "roles/run.invoker"
  member             = "serviceAccount:${google_service_account.webhook.email}"
}

# Custom role for dbt runner (if using Cloud Build)
resource "google_project_iam_custom_role" "dbt_runner" {
  count       = var.enable_cloud_build ? 1 : 0
  role_id     = "${local.resource_prefix}_dbt_runner"
  title       = "dbt Runner Role"
  description = "Custom role for dbt transformations"

  permissions = [
    "bigquery.datasets.create",
    "bigquery.datasets.delete",
    "bigquery.datasets.get",
    "bigquery.datasets.update",
    "bigquery.tables.create",
    "bigquery.tables.delete",
    "bigquery.tables.get",
    "bigquery.tables.update",
    "bigquery.tables.getData",
    "bigquery.tables.updateData",
    "bigquery.jobs.create",
    "bigquery.jobs.get",
    "bigquery.jobs.list",
  ]
}

# Service account for dbt
resource "google_service_account" "dbt" {
  count        = var.enable_cloud_build ? 1 : 0
  account_id   = "${local.resource_prefix}-dbt"
  display_name = "M-Pesa dbt Service Account"
  description  = "Service account for dbt transformations"

  depends_on = [google_project_service.required_apis]
}

# Bind custom dbt role
resource "google_project_iam_member" "dbt_custom_role" {
  count   = var.enable_cloud_build ? 1 : 0
  project = var.gcp_project_id
  role    = google_project_iam_custom_role.dbt_runner[0].id
  member  = "serviceAccount:${google_service_account.dbt[0].email}"
}

resource "google_project_iam_member" "dbt_logging" {
  count   = var.enable_cloud_build ? 1 : 0
  project = var.gcp_project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.dbt[0].email}"
}

# Service account for Cloud Build
resource "google_service_account" "cloud_build" {
  count        = var.enable_cloud_build ? 1 : 0
  account_id   = "${local.resource_prefix}-cloud-build"
  display_name = "M-Pesa Cloud Build Service Account"
  description  = "Service account for CI/CD pipeline"

  depends_on = [google_project_service.required_apis]
}

resource "google_project_iam_member" "cloud_build_editor" {
  count   = var.enable_cloud_build ? 1 : 0
  project = var.gcp_project_id
  role    = "roles/editor"
  member  = "serviceAccount:${google_service_account.cloud_build[0].email}"
}

# Outputs
output "service_accounts" {
  description = "Service accounts created"
  value = {
    webhook_sa  = google_service_account.webhook.email
    consumer_sa = google_service_account.consumer.email
    producer_sa = google_service_account.producer.email
    dataflow_sa = google_service_account.dataflow.email
    dbt_sa      = try(google_service_account.dbt[0].email, null)
    cloud_build_sa = try(google_service_account.cloud_build[0].email, null)
  }
}

output "service_account_keys" {
  description = "Service account identifiers"
  value = {
    webhook_key  = google_service_account.webhook.unique_id
    consumer_key = google_service_account.consumer.unique_id
    producer_key = google_service_account.producer.unique_id
    dataflow_key = google_service_account.dataflow.unique_id
  }
  sensitive = true
}
