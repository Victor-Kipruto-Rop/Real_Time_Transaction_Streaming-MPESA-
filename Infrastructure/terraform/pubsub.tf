# Google Cloud Pub/Sub Configuration for Event Streaming

# Main transactions topic
resource "google_pubsub_topic" "transactions" {
  name                       = local.pubsub_transactions_topic
  message_retention_duration = "${var.pubsub_subscription_retention_days * 24}h"

  labels = local.common_labels

  depends_on = [google_project_service.required_apis]
}

# Enriched transactions topic
resource "google_pubsub_topic" "enriched" {
  name                       = local.pubsub_enriched_topic
  message_retention_duration = "${var.pubsub_subscription_retention_days * 24}h"

  labels = local.common_labels

  depends_on = [google_project_service.required_apis]
}

# Dead Letter Queue (DLQ) topic
resource "google_pubsub_topic" "dead_letter" {
  name                       = local.pubsub_dlq_topic
  message_retention_duration = "${var.pubsub_subscription_retention_days * 7}h"

  labels = local.common_labels

  depends_on = [google_project_service.required_apis]
}

# Transactions subscription (for consumers)
resource "google_pubsub_subscription" "transactions" {
  name    = "${local.pubsub_transactions_topic}-sub"
  topic   = google_pubsub_topic.transactions.name
  ack_deadline_seconds = 60

  message_retention_duration = "${var.pubsub_subscription_retention_days * 24}h"
  retain_acked_messages      = true
  enable_message_ordering    = false

  # Dead letter policy
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 5
  }

  # Retry policy
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  # Push configuration (optional - for serverless)
  push_config {
    push_endpoint = try(google_cloud_run_service.webhook.status[0].url, "https://example.com/webhook")
    
    attributes = {
      x-goog-version = "v1"
    }

    authentication {
      service_account_email = google_service_account.webhook.email
    }

    oidc_token {
      service_account_email = google_service_account.webhook.email
      audience              = try(google_cloud_run_service.webhook.status[0].url, "https://example.com/webhook")
    }
  }

  labels = local.common_labels

  depends_on = [
    google_pubsub_topic.transactions,
    google_pubsub_topic.dead_letter
  ]
}

# Enriched transactions subscription
resource "google_pubsub_subscription" "enriched" {
  name             = "${local.pubsub_enriched_topic}-sub"
  topic            = google_pubsub_topic.enriched.name
  ack_deadline_seconds = 60

  message_retention_duration = "${var.pubsub_subscription_retention_days * 24}h"
  retain_acked_messages      = true
  enable_message_ordering    = false

  # Dead letter policy
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 3
  }

  # Retry policy
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  labels = local.common_labels

  depends_on = [
    google_pubsub_topic.enriched,
    google_pubsub_topic.dead_letter
  ]
}

# DLQ subscription for monitoring
resource "google_pubsub_subscription" "dead_letter" {
  name             = "${local.pubsub_dlq_topic}-sub"
  topic            = google_pubsub_topic.dead_letter.name
  ack_deadline_seconds = 60

  message_retention_duration = "${var.pubsub_subscription_retention_days * 7}h"

  labels = local.common_labels

  depends_on = [google_pubsub_topic.dead_letter]
}

# Topic IAM bindings
resource "google_pubsub_topic_iam_member" "transactions_publisher" {
  topic  = google_pubsub_topic.transactions.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.webhook.email}"
}

resource "google_pubsub_topic_iam_member" "transactions_subscriber" {
  topic  = google_pubsub_topic.transactions.name
  role   = "roles/pubsub.subscriber"
  member = "serviceAccount:${google_service_account.consumer.email}"
}

resource "google_pubsub_topic_iam_member" "enriched_publisher" {
  topic  = google_pubsub_topic.enriched.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.consumer.email}"
}

resource "google_pubsub_topic_iam_member" "enriched_subscriber" {
  topic  = google_pubsub_topic.enriched.name
  role   = "roles/pubsub.subscriber"
  member = "serviceAccount:${google_service_account.dataflow.email}"
}

resource "google_pubsub_topic_iam_member" "dlq_publisher" {
  topic  = google_pubsub_topic.dead_letter.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.consumer.email}"
}

# Monitoring for topic lag
resource "google_monitoring_alert_policy" "pubsub_oldest_unacked_message" {
  count        = var.enable_monitoring ? 1 : 0
  display_name = "${local.alert_policy_display_name} - Pub/Sub Lag"
  combiner     = "OR"

  conditions {
    display_name = "Pub/Sub Subscription Lag > 1000 messages"

    condition_threshold {
      filter          = "resource.type=\"pubsub_subscription\" AND metric.type=\"pubsub.googleapis.com/subscription/num_undelivered_messages\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 1000

      aggregations {
        alignment_period  = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  depends_on = [google_project_service.required_apis]
}

# Monitoring for old unacked messages (potential stuck consumers)
resource "google_monitoring_alert_policy" "pubsub_oldest_unacked_message_age" {
  count        = var.enable_monitoring ? 1 : 0
  display_name = "${local.alert_policy_display_name} - Pub/Sub Old Messages"
  combiner     = "OR"

  conditions {
    display_name = "Pub/Sub Oldest Unacked Message Age > 5 minutes"

    condition_threshold {
      filter          = "resource.type=\"pubsub_subscription\" AND metric.type=\"pubsub.googleapis.com/subscription/oldest_unacked_message_age\""
      duration        = "600s"
      comparison      = "COMPARISON_GT"
      threshold_value = 300000  # milliseconds (5 minutes)

      aggregations {
        alignment_period  = "60s"
        per_series_aligner = "ALIGN_MAX"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  depends_on = [google_project_service.required_apis]
}

# Outputs
output "pubsub_topics" {
  description = "Pub/Sub topic information"
  value = {
    transactions_topic = google_pubsub_topic.transactions.name
    enriched_topic     = google_pubsub_topic.enriched.name
    dead_letter_topic  = google_pubsub_topic.dead_letter.name
  }
}

output "pubsub_subscriptions" {
  description = "Pub/Sub subscription information"
  value = {
    transactions_sub = google_pubsub_subscription.transactions.name
    enriched_sub     = google_pubsub_subscription.enriched.name
    dead_letter_sub  = google_pubsub_subscription.dead_letter.name
  }
}
