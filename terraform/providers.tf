terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  cloud {
    organization = var.terraform_cloud_org

    workspaces {
      name = var.terraform_workspace
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region

  default_labels {
    environment = var.environment
    project     = "mpesa-streaming"
    managed_by  = "terraform"
    team        = var.team_label
  }
}

provider "google-beta" {
  project = var.gcp_project_id
  region  = var.gcp_region

  default_labels {
    environment = var.environment
    project     = "mpesa-streaming"
    managed_by  = "terraform"
    team        = var.team_label
  }
}

provider "random" {}
