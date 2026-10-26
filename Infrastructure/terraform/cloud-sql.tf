# Cloud SQL (PostgreSQL) Configuration for M-Pesa Pipeline

# Private service connection for Cloud SQL
resource "google_compute_global_address" "private_ip_address" {
  count         = var.enable_private_connectivity ? 1 : 0
  name          = "${local.resource_prefix}-private-ip"
  address_type  = "INTERNAL"
  address       = "10.1.0.0"
  prefix_length = 16
  network       = google_compute_network.vpc.id
  purpose       = "VPC_PEERING"

  depends_on = [google_project_service.required_apis]
}

resource "google_service_networking_connection" "private_vpc_connection" {
  count                   = var.enable_private_connectivity ? 1 : 0
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address[0].name]

  depends_on = [google_project_service.required_apis]
}

# Cloud SQL Instance
resource "google_sql_database_instance" "postgres" {
  name             = local.cloud_sql_instance_name
  database_version = var.cloud_sql_database_version
  region           = var.gcp_region
  deletion_protection = local.is_production ? true : false

  settings {
    tier              = var.cloud_sql_instance_tier
    availability_type = local.is_production ? "REGIONAL" : "ZONAL"
    disk_type        = "PD_SSD"
    disk_size        = local.is_production ? 100 : 50
    disk_autoresize  = true
    disk_autoresize_limit = local.is_production ? 1000 : 200

    # Backup configuration
    backup_configuration {
      enabled                        = local.backup_config.enabled
      start_time                     = "02:00"
      location                       = local.backup_config.backup_location
      point_in_time_recovery_enabled = local.is_production ? true : false
      transaction_log_retention_days = local.backup_config.transaction_log_retention_days
    }

    # IP configuration
    ip_configuration {
      require_ssl            = true
      enable_public_ip       = !local.is_production
      ipv4_enabled          = true
      private_network       = var.enable_private_connectivity ? google_compute_network.vpc.id : null
      authorized_networks = !local.is_production ? [
        {
          name  = "allow-all-dev"
          value = "0.0.0.0/0"
        }
      ] : []
    }

    # Database flags
    database_flags {
      name  = "log_statement"
      value = local.is_production ? "all" : "ddl"
    }

    database_flags {
      name  = "log_min_duration_statement"
      value = local.is_production ? "1000" : "5000"
    }

    database_flags {
      name  = "log_connections"
      value = "on"
    }

    database_flags {
      name  = "log_disconnections"
      value = "on"
    }

    # Insights configuration for performance monitoring
    insights_config {
      query_insights_enabled  = true
      query_plans_per_minute  = 5
      query_string_length     = 1024
      record_application_tags = true
    }

    # Location preference
    location_preference {
      zone = var.gcp_zones[0]
      secondary_zone = local.is_production ? var.gcp_zones[1] : null
    }

    # Maintenance window
    maintenance_window {
      kind           = "MAINTENANCE_WINDOW_KIND_AUTOMATIC"
      day            = 0  # Sunday
      hour           = 2
      update_track   = "stable"
    }

    # User labels
    user_labels = local.common_labels
  }

  deletion_protection = false

  depends_on = [
    google_project_service.required_apis,
    google_service_networking_connection.private_vpc_connection
  ]

  lifecycle {
    ignore_changes = [settings[0].backup_configuration[0].binary_log_enabled]
  }
}

# Database
resource "google_sql_database" "mpesa" {
  name     = local.cloud_sql_database_name
  instance = google_sql_database_instance.postgres.name

  depends_on = [google_sql_database_instance.postgres]
}

# Root user password stored in Secret Manager
resource "google_secret_manager_secret" "db_root_password" {
  secret_id = local.secret_names.db_root_password
  replication {
    automatic = true
  }

  labels = local.common_labels

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "db_root_password" {
  secret      = google_secret_manager_secret.db_root_password.id
  secret_data = var.cloud_sql_root_password
}

# Root user
resource "google_sql_user" "root" {
  name     = local.db_root_user
  instance = google_sql_database_instance.postgres.name
  password = var.cloud_sql_root_password

  depends_on = [google_sql_database.mpesa]
}

# Application user
resource "google_sql_user" "app" {
  name     = local.db_app_user
  instance = google_sql_database_instance.postgres.name
  password = var.cloud_sql_app_user_password

  depends_on = [google_sql_database.mpesa]
}

# App user password stored in Secret Manager
resource "google_secret_manager_secret" "db_app_password" {
  secret_id = local.secret_names.db_app_password
  replication {
    automatic = true
  }

  labels = local.common_labels

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "db_app_password" {
  secret      = google_secret_manager_secret.db_app_password.id
  secret_data = var.cloud_sql_app_user_password
}

# Connection parameters secret for applications
resource "google_secret_manager_secret" "db_connection_string" {
  secret_id = "${local.resource_prefix}-db-connection-string"
  replication {
    automatic = true
  }

  labels = local.common_labels

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "db_connection_string" {
  secret      = google_secret_manager_secret.db_connection_string.id
  secret_data = format(
    "postgresql://%s:%s@%s:5432/%s?sslmode=require",
    local.db_app_user,
    var.cloud_sql_app_user_password,
    google_sql_database_instance.postgres.private_ip_address,
    local.cloud_sql_database_name
  )
}

# Database monitoring alert
resource "google_monitoring_alert_policy" "cloudsql_cpu" {
  count        = var.enable_monitoring ? 1 : 0
  display_name = "${local.alert_policy_display_name} - Cloud SQL CPU"
  combiner     = "OR"

  conditions {
    display_name = "Cloud SQL CPU > 80%"

    condition_threshold {
      filter          = "resource.type=\"cloudsql_database\" AND resource.labels.database_id=\"${var.gcp_project_id}:${google_sql_database_instance.postgres.name}\" AND metric.type=\"cloudsql.googleapis.com/database/cpu/utilization\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.8

      aggregations {
        alignment_period  = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  depends_on = [google_project_service.required_apis]
}

# Database storage monitoring alert
resource "google_monitoring_alert_policy" "cloudsql_storage" {
  count        = var.enable_monitoring ? 1 : 0
  display_name = "${local.alert_policy_display_name} - Cloud SQL Storage"
  combiner     = "OR"

  conditions {
    display_name = "Cloud SQL Storage > 80%"

    condition_threshold {
      filter          = "resource.type=\"cloudsql_database\" AND resource.labels.database_id=\"${var.gcp_project_id}:${google_sql_database_instance.postgres.name}\" AND metric.type=\"cloudsql.googleapis.com/database/disk/utilization\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.8

      aggregations {
        alignment_period  = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  depends_on = [google_project_service.required_apis]
}

# Outputs
output "cloud_sql" {
  description = "Cloud SQL instance details"
  value = {
    instance_name    = google_sql_database_instance.postgres.name
    instance_address = google_sql_database_instance.postgres.private_ip_address
    public_ip        = try(google_sql_database_instance.postgres.public_ip_address, null)
    database_name    = google_sql_database.mpesa.name
    app_user         = google_sql_user.app.name
    connection_name  = google_sql_database_instance.postgres.connection_name
    region          = var.gcp_region
  }
}

output "cloud_sql_secrets" {
  description = "Secret Manager references for Cloud SQL"
  value = {
    root_password_secret = google_secret_manager_secret.db_root_password.id
    app_password_secret  = google_secret_manager_secret.db_app_password.id
    connection_string_secret = google_secret_manager_secret.db_connection_string.id
  }
  sensitive = true
}
