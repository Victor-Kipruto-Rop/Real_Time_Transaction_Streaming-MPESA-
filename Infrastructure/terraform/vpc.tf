# VPC and Networking Configuration for M-Pesa Pipeline

# VPC Network
resource "google_compute_network" "vpc" {
  name                    = local.vpc_name
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"

  depends_on = [google_project_service.required_apis]
}

# Subnet
resource "google_compute_subnetwork" "subnet" {
  name          = local.subnet_name
  ip_cidr_range = var.subnet_cidr_range
  region        = var.gcp_region
  network       = google_compute_network.vpc.id

  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata            = "INCLUDE_ALL_METADATA"
  }

  labels = local.common_labels

  depends_on = [google_compute_network.vpc]
}

# Cloud Router for Cloud NAT
resource "google_compute_router" "router" {
  count   = local.is_production ? 1 : 0
  name    = local.cloud_router_name
  region  = var.gcp_region
  network = google_compute_network.vpc.id

  bgp {
    asn = 64514
  }

  depends_on = [google_compute_network.vpc]
}

# Cloud NAT for outbound internet access
resource "google_compute_router_nat" "nat" {
  count                              = local.is_production ? 1 : 0
  name                               = local.nat_gateway_name
  router                             = google_compute_router.router[0].name
  region                             = google_compute_router.router[0].region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }

  depends_on = [google_compute_router.router]
}

# Firewall - Allow internal communication
resource "google_compute_firewall" "allow_internal" {
  name    = "${local.resource_prefix}-allow-internal"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = [var.subnet_cidr_range]

  target_tags = ["internal"]

  depends_on = [google_compute_network.vpc]
}

# Firewall - Allow SSH only in dev/staging
resource "google_compute_firewall" "allow_ssh" {
  count   = local.is_production ? 0 : 1
  name    = "${local.resource_prefix}-allow-ssh"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]

  target_tags = ["ssh"]

  depends_on = [google_compute_network.vpc]
}

# Firewall - Allow health checks
resource "google_compute_firewall" "allow_health_checks" {
  name    = "${local.resource_prefix}-allow-health-checks"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["8080", "8888"]
  }

  source_ranges = ["35.191.0.0/16", "130.211.0.0/22"]

  target_tags = ["health-check"]

  depends_on = [google_compute_network.vpc]
}

# Firewall - Allow HTTPS from Cloud Run
resource "google_compute_firewall" "allow_cloud_run" {
  name    = "${local.resource_prefix}-allow-cloud-run"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["443", "8080"]
  }

  source_tags = ["cloud-run"]
  target_tags = ["accept-cloud-run"]

  depends_on = [google_compute_network.vpc]
}

# Firewall - Allow Pub/Sub to trigger Cloud Functions/Run
resource "google_compute_firewall" "allow_pubsub" {
  name    = "${local.resource_prefix}-allow-pubsub"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["443"]
  }

  source_ranges = ["199.36.153.4/30"]

  depends_on = [google_compute_network.vpc]
}

# Firewall - Allow PostgreSQL from Cloud Run and apps
resource "google_compute_firewall" "allow_postgresql" {
  name    = "${local.resource_prefix}-allow-postgresql"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["5432"]
  }

  source_tags = ["postgres-client"]
  target_tags = ["postgres-server"]

  depends_on = [google_compute_network.vpc]
}

# Serverless VPC Connector
resource "google_vpc_access_connector" "connector" {
  name          = "${local.resource_prefix}-connector"
  region        = var.gcp_region
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.vpc.name
  min_instances = 2
  max_instances = 10

  machine_type = "f1-micro"

  depends_on = [google_compute_network.vpc]
}

# Reserved IP address for static NAT (optional, for external APIs)
resource "google_compute_address" "static" {
  count        = local.is_production ? 1 : 0
  name         = "${local.resource_prefix}-static-ip"
  address_type = "EXTERNAL"
  region       = var.gcp_region

  labels = local.common_labels

  depends_on = [google_project_service.required_apis]
}

# DNS zone for internal services
resource "google_dns_managed_zone" "internal" {
  count      = local.is_production ? 1 : 0
  name       = "${local.resource_prefix}-internal-zone"
  dns_name   = "${local.resource_prefix}.internal."
  visibility = "private"

  private_visibility_config {
    networks_list {
      network_url = google_compute_network.vpc.id
    }
  }

  labels = local.common_labels

  depends_on = [google_compute_network.vpc]
}

# DNS record for Cloud SQL (private connection)
resource "google_dns_record_set" "cloudsql" {
  count   = local.is_production ? 1 : 0
  name    = "postgres.${google_dns_managed_zone.internal[0].dns_name}"
  type    = "A"
  ttl     = 300
  managed_zone = google_dns_managed_zone.internal[0].name
  rrdatas = [
    "10.1.1.1"  # Placeholder - use Cloud SQL private IP
  ]

  depends_on = [google_dns_managed_zone.internal]
}

# Outputs
output "vpc_network" {
  description = "VPC Network information"
  value = {
    vpc_name       = google_compute_network.vpc.name
    vpc_id         = google_compute_network.vpc.id
    subnet_name    = google_compute_subnetwork.subnet.name
    subnet_id      = google_compute_subnetwork.subnet.id
    subnet_cidr    = google_compute_subnetwork.subnet.ip_cidr_range
    region         = var.gcp_region
    static_ip      = try(google_compute_address.static[0].address, null)
  }
}

output "vpc_connectors" {
  description = "Serverless VPC Connector information"
  value = {
    connector_name = google_vpc_access_connector.connector.name
    connector_id   = google_vpc_access_connector.connector.id
  }
}
