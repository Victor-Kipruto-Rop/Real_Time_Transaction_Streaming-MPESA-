# Secret Manager Configuration for M-Pesa Pipeline

# Daraja API Key Secret
resource "google_secret_manager_secret" "daraja_api_key" {
  secret_id = local.secret_names.daraja_api_key
  replication {
    automatic = true
  }

  labels = local.common_labels

  depends_on = [google_project_service.required_apis]
}

# Daraja API Secret
resource "google_secret_manager_secret" "daraja_api_secret" {
  secret_id = local.secret_names.daraja_api_secret
  replication {
    automatic = true
  }

  labels = local.common_labels

  depends_on = [google_project_service.required_apis]
}

# Webhook Signing Key
resource "google_secret_manager_secret" "webhook_signing_key" {
  secret_id = local.secret_names.webhook_signing_key
  replication {
    automatic = true
  }

  labels = local.common_labels

  depends_on = [google_project_service.required_apis]
}

# GCP Service Account Key Secret
resource "google_secret_manager_secret" "gcp_service_account_key" {
  secret_id = local.secret_names.service_account_key
  replication {
    automatic = true
  }

  labels = local.common_labels

  depends_on = [google_project_service.required_apis]
}

# Grant service accounts permission to access secrets
resource "google_secret_manager_secret_iam_member" "webhook_daraja_key" {
  secret_id = google_secret_manager_secret.daraja_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.webhook.email}"
}

resource "google_secret_manager_secret_iam_member" "webhook_signing_key" {
  secret_id = google_secret_manager_secret.webhook_signing_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.webhook.email}"
}

resource "google_secret_manager_secret_iam_member" "webhook_daraja_secret" {
  secret_id = google_secret_manager_secret.daraja_api_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.webhook.email}"
}

resource "google_secret_manager_secret_iam_member" "consumer_daraja_key" {
  secret_id = google_secret_manager_secret.daraja_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.consumer.email}"
}

resource "google_secret_manager_secret_iam_member" "producer_daraja_key" {
  secret_id = google_secret_manager_secret.daraja_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.producer.email}"
}

resource "google_secret_manager_secret_iam_member" "dataflow_daraja_key" {
  secret_id = google_secret_manager_secret.daraja_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.dataflow.email}"
}

# Secret versions with placeholder values (manually set after creation)
resource "google_secret_manager_secret_version" "daraja_api_key" {
  secret      = google_secret_manager_secret.daraja_api_key.id
  secret_data = "PLACEHOLDER_UPDATE_REQUIRED"

  lifecycle {
    ignore_changes = [secret_data]
  }
}

resource "google_secret_manager_secret_version" "daraja_api_secret" {
  secret      = google_secret_manager_secret.daraja_api_secret.id
  secret_data = "PLACEHOLDER_UPDATE_REQUIRED"

  lifecycle {
    ignore_changes = [secret_data]
  }
}

resource "google_secret_manager_secret_version" "webhook_signing_key" {
  secret      = google_secret_manager_secret.webhook_signing_key.id
  secret_data = "PLACEHOLDER_UPDATE_REQUIRED"

  lifecycle {
    ignore_changes = [secret_data]
  }
}

# Secret for service account key
resource "google_secret_manager_secret_version" "gcp_service_account_key" {
  secret      = google_secret_manager_secret.gcp_service_account_key.id
  secret_data = "PLACEHOLDER_UPDATE_REQUIRED"

  lifecycle {
    ignore_changes = [secret_data]
  }
}

# Secret rotation alert
resource "google_monitoring_alert_policy" "secret_rotation_reminder" {
  count        = var.enable_monitoring ? 1 : 0
  display_name = "${local.alert_policy_display_name} - Secret Rotation Reminder"
  combiner     = "OR"

  documentation {
    content = "Reminder to rotate secrets. Secrets should be rotated every 90 days."
  }

  # This is a manual reminder alert that would need to be set up differently
  # For now, just create an alert notification channel

  notification_channels = [google_monitoring_notification_channel.email.id]

  depends_on = [google_project_service.required_apis]
}

# Audit logging for secret access
resource "google_project_iam_audit_config" "secrets_audit" {
  service = "secretmanager.googleapis.com"
  project = var.gcp_project_id

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

# Outputs
output "secrets" {
  description = "Secret Manager references"
  value = {
    daraja_api_key           = google_secret_manager_secret.daraja_api_key.id
    daraja_api_secret        = google_secret_manager_secret.daraja_api_secret.id
    webhook_signing_key      = google_secret_manager_secret.webhook_signing_key.id
    db_root_password         = google_secret_manager_secret.db_root_password.id
    db_app_password          = google_secret_manager_secret.db_app_password.id
    db_connection_string     = google_secret_manager_secret.db_connection_string.id
    gcp_service_account_key  = google_secret_manager_secret.gcp_service_account_key.id
  }
  sensitive = true
}

output "secret_access_instructions" {
  description = "Instructions for updating secrets"
  value = {
    daraja_api_key = "gcloud secrets versions add ${google_secret_manager_secret.daraja_api_key.secret_id} --data-file=- < /path/to/key"
    daraja_api_secret = "gcloud secrets versions add ${google_secret_manager_secret.daraja_api_secret.secret_id} --data-file=- < /path/to/secret"
    webhook_signing_key = "gcloud secrets versions add ${google_secret_manager_secret.webhook_signing_key.secret_id} --data-file=- < /path/to/key"
  }
}
