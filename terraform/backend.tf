# Terraform Backend Configuration
# This file configures where and how Terraform state is stored and locked

terraform {
  # Uncomment and configure for remote state management
  # backend "gcs" {
  #   bucket  = "YOUR-PROJECT-ID-tfstate"
  #   prefix  = "mpesa-streaming/prod"
  # }

  # Uncomment and configure for Terraform Cloud
  # cloud {
  #   organization = "YOUR-ORG"
  #   workspaces {
  #     name = "mpesa-streaming-prod"
  #   }
  # }
}

# Local backend (default - for development only)
# WARNING: Do not use local backend for production
# Comment this out when using remote backend
