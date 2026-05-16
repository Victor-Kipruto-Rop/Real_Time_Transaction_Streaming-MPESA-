# BigQuery configuration for M-Pesa data warehouse

# Raw layer dataset - incoming data
resource "google_bigquery_dataset" "raw" {
  dataset_id      = local.bigquery_raw_dataset
  friendly_name   = "M-Pesa Raw Data"
  description     = "Raw M-Pesa transaction data from Daraja API"
  location        = var.bigquery_dataset_location
  default_table_expiration_ms = var.bigquery_tables_expiration_ms

  access {
    role          = "OWNER"
    user_by_email = google_service_account.webhook.email
  }

  access {
    role          = "EDITOR"
    user_by_email = google_service_account.consumer.email
  }

  access {
    role          = "VIEWER"
    user_by_email = google_service_account.dataflow.email
  }

  labels = local.common_labels

  depends_on = [google_project_service.required_apis]
}

# Staging layer dataset - transformed data
resource "google_bigquery_dataset" "staging" {
  dataset_id      = local.bigquery_staging_dataset
  friendly_name   = "M-Pesa Staging"
  description     = "Staging layer for dbt transformations"
  location        = var.bigquery_dataset_location
  default_table_expiration_ms = var.bigquery_tables_expiration_ms

  access {
    role          = "EDITOR"
    user_by_email = google_service_account.consumer.email
  }

  access {
    role          = "VIEWER"
    user_by_email = google_service_account.dataflow.email
  }

  labels = local.common_labels

  depends_on = [google_project_service.required_apis]
}

# Analytics layer dataset - business metrics
resource "google_bigquery_dataset" "analytics" {
  dataset_id      = local.bigquery_analytics_dataset
  friendly_name   = "M-Pesa Analytics"
  description     = "Analytics ready data for dashboards and reports"
  location        = var.bigquery_dataset_location

  access {
    role          = "EDITOR"
    user_by_email = google_service_account.consumer.email
  }

  access {
    role          = "VIEWER"
    user_by_email = google_service_account.dataflow.email
  }

  labels = local.common_labels

  depends_on = [google_project_service.required_apis]
}

# Archive layer dataset - historical data
resource "google_bigquery_dataset" "archive" {
  dataset_id      = local.bigquery_archive_dataset
  friendly_name   = "M-Pesa Archive"
  description     = "Long-term archived data and audit logs"
  location        = var.bigquery_dataset_location

  labels = local.common_labels

  depends_on = [google_project_service.required_apis]
}

# Raw transactions table
resource "google_bigquery_table" "raw_transactions" {
  dataset_id = google_bigquery_dataset.raw.dataset_id
  table_id   = "mpesa_raw_transactions"
  description = "Raw M-Pesa transactions from Daraja API"

  schema = jsonencode([
    {
      name        = "transaction_id"
      type        = "STRING"
      description = "Unique transaction identifier"
      mode        = "REQUIRED"
    },
    {
      name        = "timestamp"
      type        = "TIMESTAMP"
      description = "Transaction timestamp"
      mode        = "REQUIRED"
    },
    {
      name        = "amount"
      type        = "NUMERIC"
      description = "Transaction amount in KES"
      mode        = "REQUIRED"
    },
    {
      name        = "phone_number"
      type        = "STRING"
      description = "Customer phone number (masked)"
      mode        = "REQUIRED"
    },
    {
      name        = "merchant_code"
      type        = "STRING"
      description = "Merchant/Paybill/Till code"
      mode        = "REQUIRED"
    },
    {
      name        = "transaction_type"
      type        = "STRING"
      description = "Transaction type (C2B, B2C, etc.)"
      mode        = "REQUIRED"
    },
    {
      name        = "status"
      type        = "STRING"
      description = "Transaction status"
      mode        = "REQUIRED"
    },
    {
      name        = "reference"
      type        = "STRING"
      description = "Transaction reference"
      mode        = "NULLABLE"
    },
    {
      name        = "description"
      type        = "STRING"
      description = "Transaction description"
      mode        = "NULLABLE"
    },
    {
      name        = "raw_payload"
      type        = "JSON"
      description = "Complete raw JSON payload"
      mode        = "NULLABLE"
    },
    {
      name        = "_ingestion_timestamp"
      type        = "TIMESTAMP"
      description = "Data ingestion timestamp"
      mode        = "REQUIRED"
    },
    {
      name        = "_partition_date"
      type        = "DATE"
      description = "Partition column for optimization"
      mode        = "REQUIRED"
    }
  ])

  time_partitioning {
    type          = "DAY"
    field         = "_partition_date"
    expiration_ms = var.bigquery_tables_expiration_ms
  }

  clustering = ["transaction_type", "merchant_code", "status"]

  labels = local.common_labels

  depends_on = [
    google_bigquery_dataset.raw,
    google_project_service.required_apis
  ]
}

# Staging transactions table (dbt model output)
resource "google_bigquery_table" "staging_transactions" {
  dataset_id = google_bigquery_dataset.staging.dataset_id
  table_id   = "stg_mpesa_transactions"
  description = "Staged and cleansed M-Pesa transactions"

  schema = jsonencode([
    {
      name        = "transaction_id"
      type        = "STRING"
      description = "Unique transaction identifier"
      mode        = "REQUIRED"
    },
    {
      name        = "transaction_date"
      type        = "DATE"
      description = "Transaction date"
      mode        = "REQUIRED"
    },
    {
      name        = "transaction_hour"
      type        = "STRING"
      description = "Transaction hour (HH format)"
      mode        = "REQUIRED"
    },
    {
      name        = "amount"
      type        = "NUMERIC"
      description = "Transaction amount in KES"
      mode        = "REQUIRED"
    },
    {
      name        = "merchant_code"
      type        = "STRING"
      description = "Merchant/Paybill/Till code"
      mode        = "REQUIRED"
    },
    {
      name        = "merchant_category"
      type        = "STRING"
      description = "Merchant category"
      mode        = "NULLABLE"
    },
    {
      name        = "transaction_type"
      type        = "STRING"
      description = "Transaction type (C2B, B2C)"
      mode        = "REQUIRED"
    },
    {
      name        = "status"
      type        = "STRING"
      description = "Transaction status"
      mode        = "REQUIRED"
    },
    {
      name        = "county_code"
      type        = "STRING"
      description = "County code (extracted from merchant)"
      mode        = "NULLABLE"
    },
    {
      name        = "is_fraud_suspected"
      type        = "BOOLEAN"
      description = "Fraud flag (from ML model)"
      mode        = "NULLABLE"
    },
    {
      name        = "dbt_created_at"
      type        = "TIMESTAMP"
      description = "dbt transformation timestamp"
      mode        = "REQUIRED"
    }
  ])

  time_partitioning {
    type  = "DAY"
    field = "transaction_date"
  }

  clustering = ["transaction_type", "merchant_code", "county_code", "status"]

  labels = local.common_labels

  depends_on = [
    google_bigquery_dataset.staging,
    google_project_service.required_apis
  ]
}

# Analytics hourly volumes table (mart)
resource "google_bigquery_table" "analytics_hourly_volumes" {
  dataset_id = google_bigquery_dataset.analytics.dataset_id
  table_id   = "mart_hourly_transaction_volumes"
  description = "Hourly transaction volume metrics"

  schema = jsonencode([
    {
      name        = "date"
      type        = "DATE"
      description = "Date"
      mode        = "REQUIRED"
    },
    {
      name        = "hour"
      type        = "STRING"
      description = "Hour (HH format)"
      mode        = "REQUIRED"
    },
    {
      name        = "transaction_type"
      type        = "STRING"
      description = "Transaction type"
      mode        = "REQUIRED"
    },
    {
      name        = "total_transactions"
      type        = "INTEGER"
      description = "Total transaction count"
      mode        = "REQUIRED"
    },
    {
      name        = "total_amount"
      type        = "NUMERIC"
      description = "Total transaction amount in KES"
      mode        = "REQUIRED"
    },
    {
      name        = "average_amount"
      type        = "NUMERIC"
      description = "Average transaction amount"
      mode        = "REQUIRED"
    },
    {
      name        = "successful_transactions"
      type        = "INTEGER"
      description = "Count of successful transactions"
      mode        = "REQUIRED"
    },
    {
      name        = "failed_transactions"
      type        = "INTEGER"
      description = "Count of failed transactions"
      mode        = "REQUIRED"
    },
    {
      name        = "success_rate_percent"
      type        = "NUMERIC"
      description = "Success rate percentage"
      mode        = "REQUIRED"
    }
  ])

  time_partitioning {
    type  = "DAY"
    field = "date"
  }

  clustering = ["transaction_type", "hour"]

  labels = local.common_labels

  depends_on = [
    google_bigquery_dataset.analytics,
    google_project_service.required_apis
  ]
}

# Analytics county heatmap table (mart)
resource "google_bigquery_table" "analytics_county_heatmap" {
  dataset_id = google_bigquery_dataset.analytics.dataset_id
  table_id   = "mart_county_transaction_heatmap"
  description = "Transaction volume heatmap by county"

  schema = jsonencode([
    {
      name        = "date"
      type        = "DATE"
      description = "Date"
      mode        = "REQUIRED"
    },
    {
      name        = "county_code"
      type        = "STRING"
      description = "County code"
      mode        = "REQUIRED"
    },
    {
      name        = "county_name"
      type        = "STRING"
      description = "County name"
      mode        = "NULLABLE"
    },
    {
      name        = "transaction_count"
      type        = "INTEGER"
      description = "Transaction count for county"
      mode        = "REQUIRED"
    },
    {
      name        = "transaction_volume"
      type        = "NUMERIC"
      description = "Total transaction volume in KES"
      mode        = "REQUIRED"
    },
    {
      name        = "average_transaction_size"
      type        = "NUMERIC"
      description = "Average transaction size"
      mode        = "REQUIRED"
    }
  ])

  time_partitioning {
    type  = "DAY"
    field = "date"
  }

  clustering = ["county_code"]

  labels = local.common_labels

  depends_on = [
    google_bigquery_dataset.analytics,
    google_project_service.required_apis
  ]
}

# BigQuery dataset IAM bindings
resource "google_bigquery_dataset_iam_member" "raw_editor" {
  dataset_id = google_bigquery_dataset.raw.dataset_id
  role       = "roles/bigquery.editor"
  member     = "serviceAccount:${google_service_account.consumer.email}"
}

resource "google_bigquery_dataset_iam_member" "analytics_viewer" {
  dataset_id = google_bigquery_dataset.analytics.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.dataflow.email}"
}

# Outputs
output "bigquery_datasets" {
  description = "BigQuery dataset information"
  value = {
    raw_dataset    = google_bigquery_dataset.raw.dataset_id
    staging_dataset = google_bigquery_dataset.staging.dataset_id
    analytics_dataset = google_bigquery_dataset.analytics.dataset_id
    archive_dataset = google_bigquery_dataset.archive.dataset_id
    region         = var.bigquery_dataset_location
  }
}

output "bigquery_tables" {
  description = "BigQuery table information"
  value = {
    raw_transactions        = google_bigquery_table.raw_transactions.table_id
    staging_transactions    = google_bigquery_table.staging_transactions.table_id
    hourly_volumes         = google_bigquery_table.analytics_hourly_volumes.table_id
    county_heatmap         = google_bigquery_table.analytics_county_heatmap.table_id
  }
}
