# Monitoring and Observability Configuration

# Log sink for Cloud Logging (export to BigQuery)
resource "google_logging_project_sink" "all_logs" {
  count            = var.enable_logging ? 1 : 0
  name             = "${local.resource_prefix}-all-logs-sink"
  destination      = "bigquery.googleapis.com/projects/${var.gcp_project_id}/datasets/${google_bigquery_dataset.archive.dataset_id}"
  filter           = "severity>='WARNING' OR resource.type='cloud_run_revision' OR resource.type='cloudsql_database'"
  unique_writer_identity = true

  depends_on = [google_project_service.required_apis]
}

# Grant logging service account permission to write to BigQuery
resource "google_bigquery_dataset_iam_member" "logs_sink_writer" {
  count      = var.enable_logging ? 1 : 0
  dataset_id = google_bigquery_dataset.archive.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_logging_project_sink.all_logs[0].writer_identity

  depends_on = [google_project_service.required_apis]
}

# Uptime check for webhook endpoint
resource "google_monitoring_uptime_check_config" "webhook" {
  count           = var.enable_monitoring ? 1 : 0
  display_name    = "${local.alert_policy_display_name} - Webhook Uptime"
  timeout         = "10s"
  period          = "60s"
  selected_regions = ["USA", "EUROPE", "ASIA_PACIFIC"]

  http_check {
    path           = "/health"
    port           = 443
    request_method = "GET"
    use_ssl        = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      host = "example.com"  # Replace with actual webhook URL
    }
  }

  depends_on = [google_project_service.required_apis]
}

# Alert policy for uptime check
resource "google_monitoring_alert_policy" "webhook_uptime" {
  count        = var.enable_monitoring ? 1 : 0
  display_name = "${local.alert_policy_display_name} - Webhook Down"
  combiner     = "OR"

  conditions {
    display_name = "Webhook Service Down"

    condition_threshold {
      filter          = "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" AND resource.type=\"uptime_url\""
      duration        = "300s"
      comparison      = "COMPARISON_LT"
      threshold_value = 1

      aggregations {
        alignment_period  = "60s"
        per_series_aligner = "ALIGN_FRACTION_TRUE"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  depends_on = [google_project_service.required_apis]
}

# Custom metric for transaction volume
resource "google_monitoring_metric_descriptor" "transaction_volume" {
  type        = "custom.googleapis.com/mpesa/transaction_volume"
  metric_kind = "GAUGE"
  value_type  = "INT64"
  display_name = "M-Pesa Transaction Volume (per minute)"
  description = "Number of transactions processed per minute"

  labels {
    key         = "transaction_type"
    value_type  = "STRING"
    description = "Type of transaction (C2B, B2C, etc.)"
  }

  labels {
    key         = "status"
    value_type  = "STRING"
    description = "Transaction status (success, failure)"
  }

  depends_on = [google_project_service.required_apis]
}

# Custom metric for latency
resource "google_monitoring_metric_descriptor" "transaction_latency" {
  type        = "custom.googleapis.com/mpesa/transaction_latency_ms"
  metric_kind = "DISTRIBUTION"
  value_type  = "DISTRIBUTION"
  display_name = "M-Pesa Transaction Latency"
  description = "Latency of transaction processing in milliseconds"

  labels {
    key         = "transaction_type"
    value_type  = "STRING"
    description = "Type of transaction"
  }

  depends_on = [google_project_service.required_apis]
}

# Dashboard for M-Pesa metrics
resource "google_monitoring_dashboard" "mpesa" {
  count          = var.enable_monitoring ? 1 : 0
  dashboard_json = jsonencode({
    displayName = "M-Pesa Streaming Pipeline"
    mosaicLayout = {
      columns = 12
      tiles = [
        {
          width  = 6
          height = 4
          widget = {
            title = "Transaction Volume (Last 24h)"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"custom.googleapis.com/mpesa/transaction_volume\""
                    }
                  }
                }
              ]
            }
          }
        },
        {
          xPos   = 6
          width  = 6
          height = 4
          widget = {
            title = "Transaction Latency (P95)"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"custom.googleapis.com/mpesa/transaction_latency_ms\""
                    }
                  }
                }
              ]
            }
          }
        },
        {
          yPos   = 4
          width  = 6
          height = 4
          widget = {
            title = "Cloud Run Error Rate"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"run.googleapis.com/request_count\" AND resource.type=\"cloud_run_revision\""
                    }
                  }
                }
              ]
            }
          }
        },
        {
          xPos   = 6
          yPos   = 4
          width  = 6
          height = 4
          widget = {
            title = "Pub/Sub Subscription Lag"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"pubsub.googleapis.com/subscription/num_undelivered_messages\""
                    }
                  }
                }
              ]
            }
          }
        },
        {
          yPos   = 8
          width  = 6
          height = 4
          widget = {
            title = "Cloud SQL CPU Utilization"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"cloudsql.googleapis.com/database/cpu/utilization\" AND resource.type=\"cloudsql_database\""
                    }
                  }
                }
              ]
            }
          }
        },
        {
          xPos   = 6
          yPos   = 8
          width  = 6
          height = 4
          widget = {
            title = "BigQuery Jobs"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"bigquery.googleapis.com/job/num_completed_jobs\""
                    }
                  }
                }
              ]
            }
          }
        }
      ]
    }
  })

  depends_on = [google_project_service.required_apis]
}

# Log-based metrics
resource "google_logging_metric" "webhook_errors" {
  count  = var.enable_logging ? 1 : 0
  name   = "${local.resource_prefix}-webhook-errors"
  filter = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${google_cloud_run_service.webhook.name}\" AND severity=\"ERROR\""

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    display_name = "Webhook Errors"

    labels {
      key         = "service"
      value_type  = "STRING"
      description = "Service generating the error"
    }
  }

  depends_on = [google_project_service.required_apis]
}

# Alert policy for high error rate in logs
resource "google_monitoring_alert_policy" "webhook_high_error_rate" {
  count        = var.enable_logging ? 1 : 0
  display_name = "${local.alert_policy_display_name} - High Error Rate"
  combiner     = "OR"

  conditions {
    display_name = "Webhook Errors > 10 in 5 minutes"

    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/${google_logging_metric.webhook_errors[0].name}\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 10

      aggregations {
        alignment_period  = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  depends_on = [google_project_service.required_apis]
}

# Outputs
output "monitoring" {
  description = "Monitoring setup information"
  value = {
    notification_channel = google_monitoring_notification_channel.email.id
    dashboard_name       = try(google_monitoring_dashboard.mpesa[0].dashboard_json, "N/A")
    logging_enabled      = var.enable_logging
    monitoring_enabled   = var.enable_monitoring
  }
}
