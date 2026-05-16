# Cloud Run Configuration for Webhook Receiver and Services

# Cloud Run Service - Webhook Receiver
resource "google_cloud_run_service" "webhook" {
  name     = local.webhook_service_name
  location = var.gcp_region

  template {
    spec {
      service_account_name = google_service_account.webhook.email

      containers {
        image = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${local.artifact_registry_repo_name}/webhook:latest"
        
        ports {
          container_port = 8080
          name           = "http1"
        }

        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }

        env {
          name  = "GCP_PROJECT_ID"
          value = var.gcp_project_id
        }

        env {
          name  = "GCP_REGION"
          value = var.gcp_region
        }

        env {
          name  = "PUBSUB_TOPIC"
          value = google_pubsub_topic.transactions.name
        }

        env {
          name = "DARAJA_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.daraja_api_key.secret_id
              key  = "latest"
            }
          }
        }

        env {
          name = "WEBHOOK_SIGNING_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.webhook_signing_key.secret_id
              key  = "latest"
            }
          }
        }

        env {
          name = "DATABASE_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.db_connection_string.secret_id
              key  = "latest"
            }
          }
        }

        resources {
          limits = {
            cpu    = var.cloud_run_webhook_cpu
            memory = var.cloud_run_webhook_memory
          }
        }
      }

      timeout_seconds       = var.cloud_run_webhook_timeout
      service_account_name  = google_service_account.webhook.email
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale"      = var.cloud_run_min_instances
        "autoscaling.knative.dev/maxScale"      = var.cloud_run_max_instances
        "run.googleapis.com/cpu-throttling"     = "false"
        "run.googleapis.com/vpc-access-egress"  = "private-ranges-only"
        "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.connector.name
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  autogenerate_revision_name = true

  depends_on = [
    google_project_service.required_apis,
    google_artifact_registry_repository.docker
  ]
}

# Make service public (with authentication)
resource "google_cloud_run_service_iam_member" "webhook_public" {
  service = google_cloud_run_service.webhook.name
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.webhook.email}"
  location = var.gcp_region
}

# Cloud Run Service - Consumer (optional, if running outside Kubernetes)
resource "google_cloud_run_service" "consumer" {
  count    = local.is_dev ? 1 : 0
  name     = local.consumer_service_name
  location = var.gcp_region

  template {
    spec {
      service_account_name = google_service_account.consumer.email

      containers {
        image = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${local.artifact_registry_repo_name}/consumer:latest"
        
        ports {
          container_port = 8080
        }

        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }

        env {
          name  = "GCP_PROJECT_ID"
          value = var.gcp_project_id
        }

        env {
          name  = "PUBSUB_TOPIC_IN"
          value = google_pubsub_topic.transactions.name
        }

        env {
          name  = "PUBSUB_TOPIC_OUT"
          value = google_pubsub_topic.enriched.name
        }

        env {
          name  = "BIGQUERY_DATASET"
          value = google_bigquery_dataset.staging.dataset_id
        }

        env {
          name = "DATABASE_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.db_connection_string.secret_id
              key  = "latest"
            }
          }
        }

        resources {
          limits = {
            cpu    = "2"
            memory = "1Gi"
          }
        }
      }

      timeout_seconds = 3600
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = 1
        "autoscaling.knative.dev/maxScale" = var.cloud_run_max_instances
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_project_service.required_apis,
    google_artifact_registry_repository.docker
  ]
}

# Artifact Registry Repository for Docker Images
resource "google_artifact_registry_repository" "docker" {
  location      = var.gcp_region
  repository_id = local.artifact_registry_repo_name
  format        = var.artifact_registry_repository_format
  description   = "Docker repository for M-Pesa streaming pipeline"

  docker_config {
    immutable_tags = false
  }

  labels = local.common_labels

  depends_on = [google_project_service.required_apis]
}

# Grant service accounts permission to pull images
resource "google_artifact_registry_repository_iam_member" "webhook_reader" {
  repository = google_artifact_registry_repository.docker.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.webhook.email}"
  location   = var.gcp_region
}

resource "google_artifact_registry_repository_iam_member" "consumer_reader" {
  count      = local.is_dev ? 1 : 0
  repository = google_artifact_registry_repository.docker.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.consumer.email}"
  location   = var.gcp_region
}

# Cloud Run monitoring - Response time
resource "google_monitoring_alert_policy" "cloud_run_latency" {
  count        = var.enable_monitoring ? 1 : 0
  display_name = "${local.alert_policy_display_name} - Cloud Run Latency"
  combiner     = "OR"

  conditions {
    display_name = "Cloud Run High Latency (P95 > 1s)"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_latencies\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 1000000000  # 1 second in nanoseconds

      aggregations {
        alignment_period    = "60s"
        per_series_aligner  = "ALIGN_PERCENTILE_95"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  depends_on = [google_project_service.required_apis]
}

# Cloud Run monitoring - Error rate
resource "google_monitoring_alert_policy" "cloud_run_errors" {
  count        = var.enable_monitoring ? 1 : 0
  display_name = "${local.alert_policy_display_name} - Cloud Run Errors"
  combiner     = "OR"

  conditions {
    display_name = "Cloud Run Error Rate > 5%"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\" AND resource.labels.service_name=\"${google_cloud_run_service.webhook.name}\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
        cross_series_reducer = "REDUCE_FRACTION_LESS_THAN"
        group_by_fields = ["resource.label.response_code"]
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  depends_on = [google_project_service.required_apis]
}

# Outputs
output "cloud_run_services" {
  description = "Cloud Run service information"
  value = {
    webhook_service_url = google_cloud_run_service.webhook.status[0].url
    webhook_service_name = google_cloud_run_service.webhook.name
    consumer_service_url = try(google_cloud_run_service.consumer[0].status[0].url, null)
    consumer_service_name = try(google_cloud_run_service.consumer[0].name, null)
  }
}

output "artifact_registry" {
  description = "Artifact Registry information"
  value = {
    repository_name = google_artifact_registry_repository.docker.repository_id
    repository_url  = google_artifact_registry_repository.docker.repository_format
    region         = google_artifact_registry_repository.docker.location
  }
}
