# M-Pesa Analytics Platform - Comprehensive Makefile
# Complete automation for development and production

.PHONY: help setup verify clean test run-all
.DEFAULT_GOAL := help

# Colors
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m

PYTHON := python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
DOCKER_COMPOSE := docker compose
POSTGRES_HOST ?= localhost
POSTGRES_HOST_PORT ?= 5432
POSTGRES_PORT ?= $(POSTGRES_HOST_PORT)
POSTGRES_DB ?= mpesa_analytics
POSTGRES_USER ?= data_engineer
POSTGRES_PASSWORD ?= change_me
DBT_LOG_PATH ?= /tmp/mpesa-dbt-logs
DBT_TARGET_PATH ?= /tmp/mpesa-dbt-target

help:
	@echo "$(BLUE)M-Pesa Analytics Platform - Complete Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Setup:$(NC)"
	@echo "  make setup              - Setup virtual environment and dependencies"
	@echo "  make verify             - Verify all components working"
	@echo "  make test-api           - Test Daraja API credentials"
	@echo ""
	@echo "$(GREEN)Infrastructure:$(NC)"
	@echo "  make infra-up           - Start Docker services"
	@echo "  make infra-down         - Stop Docker services"
	@echo "  make grafana-up         - Start Grafana (port 3000)"
	@echo ""
	@echo "$(GREEN)Data Processing:$(NC)"
	@echo "  make ingest             - Start Kafka consumer"
	@echo "  make transform          - Run DBT models"
	@echo "  make analytics          - Run advanced analytics"
	@echo "  make fraud-detection    - Train fraud detection models"
	@echo "  make dashboards         - Generate Grafana dashboards"
	@echo ""
	@echo "$(GREEN)Database:$(NC)"
	@echo "  make db-connect         - Connect to PostgreSQL"
	@echo "  make db-status          - Show database stats"
	@echo "  make db-backup          - Backup database"
	@echo ""
	@echo "$(GREEN)Testing & Quality:$(NC)"
	@echo "  make test               - Run all tests"
	@echo "  make lint               - Run linting"
	@echo "  make format             - Format code"
	@echo ""
	@echo "$(GREEN)Production:$(NC)"
	@echo "  make security-check     - Review security policies"
	@echo "  make gcp-setup          - Setup GCP project"
	@echo "  make build              - Build Docker image"
	@echo ""
	@echo "$(GREEN)Monitoring:$(NC)"
	@echo "  make health-check       - Run health checks"
	@echo "  make logs               - View logs"
	@echo ""
	@echo "$(GREEN)Utilities:$(NC)"
	@echo "  make clean              - Clean up temporary files"
	@echo "  make run-all            - Run all components"
	@echo ""

# ============================================================================
# SETUP
# ============================================================================

setup:
	@echo "$(BLUE)Setting up M-Pesa Analytics Platform...$(NC)"
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv $(VENV); \
	fi
	@$(VENV_PYTHON) -m pip install -r requirements.txt
	@echo "$(GREEN)✓ Setup complete$(NC)"

verify:
	@echo "$(BLUE)Verifying M-Pesa Analytics Platform...$(NC)"
	@$(VENV_PYTHON) scripts/verify_setup.py
	@echo "$(GREEN)✓ Verification complete$(NC)"

test-api:
	@echo "$(BLUE)Testing Daraja API...$(NC)"
	@$(VENV_PYTHON) -m pytest tests/test_daraja_client.py -v
	@echo "$(GREEN)✓ API test complete$(NC)"

# ============================================================================
# INFRASTRUCTURE
# ============================================================================

infra-up:
	@echo "$(BLUE)Starting Docker infrastructure...$(NC)"
	@$(DOCKER_COMPOSE) up -d
	@sleep 10
	@$(DOCKER_COMPOSE) ps
	@echo "$(GREEN)✓ Infrastructure up$(NC)"

infra-down:
	@echo "$(YELLOW)Stopping Docker infrastructure...$(NC)"
	@$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✓ Infrastructure down$(NC)"

grafana-up:
	@echo "$(BLUE)Starting Grafana...$(NC)"
	@docker run -d --name mpesa_grafana --network mpesa_network \
		-p 3000:3000 \
		-e "GF_SECURITY_ADMIN_PASSWORD=admin123" \
		grafana/grafana:latest 2>/dev/null || true
	@echo "$(GREEN)✓ Grafana running at http://localhost:3000$(NC)"
	@echo "   Username: admin, Password: admin123"

# ============================================================================
# DATA PROCESSING
# ============================================================================

ingest:
	@echo "$(BLUE)Starting Kafka consumer...$(NC)"
	@$(VENV_PYTHON) ingestion/kafka_consumer.py

transform:
	@echo "$(BLUE)Running DBT transformations...$(NC)"
	@POSTGRES_HOST=$(POSTGRES_HOST) POSTGRES_PORT=$(POSTGRES_PORT) POSTGRES_DB=$(POSTGRES_DB) POSTGRES_USER=$(POSTGRES_USER) POSTGRES_PASSWORD=$(POSTGRES_PASSWORD) \
		$(VENV_PYTHON) -m dbt.cli.main --log-path $(DBT_LOG_PATH) run --target-path $(DBT_TARGET_PATH) --project-dir dbt --profiles-dir dbt
	@POSTGRES_HOST=$(POSTGRES_HOST) POSTGRES_PORT=$(POSTGRES_PORT) POSTGRES_DB=$(POSTGRES_DB) POSTGRES_USER=$(POSTGRES_USER) POSTGRES_PASSWORD=$(POSTGRES_PASSWORD) \
		$(VENV_PYTHON) -m dbt.cli.main --log-path $(DBT_LOG_PATH) test --target-path $(DBT_TARGET_PATH) --project-dir dbt --profiles-dir dbt
	@echo "$(GREEN)✓ Transformations complete$(NC)"

analytics:
	@echo "$(BLUE)Running advanced analytics...$(NC)"
	@mkdir -p reports
	@$(VENV_PYTHON) analytics/advanced_analytics.py | tee reports/analytics_report.json
	@echo "$(GREEN)✓ Analytics complete$(NC)"

fraud-detection:
	@echo "$(BLUE)Training fraud detection models...$(NC)"
	@$(VENV_PYTHON) ml/fraud_detection.py
	@echo "$(GREEN)✓ Fraud models trained$(NC)"

dashboards:
	@echo "$(BLUE)Generating dashboards...$(NC)"
	@$(VENV_PYTHON) dashboards/grafana_dashboards.py
	@echo "$(GREEN)✓ Dashboards generated$(NC)"

# ============================================================================
# DATABASE
# ============================================================================

db-connect:
	@psql -h $(POSTGRES_HOST) -p $(POSTGRES_PORT) -U $(POSTGRES_USER) -d $(POSTGRES_DB)

db-status:
	@echo "$(BLUE)Database Statistics:$(NC)"
	@psql -h $(POSTGRES_HOST) -p $(POSTGRES_PORT) -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c \
		"SELECT COUNT(*) as raw_transactions FROM mpesa_transactions_raw; SELECT COUNT(DISTINCT phone_number) as unique_customers FROM mpesa_transactions_raw; SELECT SUM(amount) as total_volume FROM mpesa_transactions_raw WHERE DATE(transaction_time) = CURRENT_DATE;"

db-backup:
	@echo "$(BLUE)Backing up database...$(NC)"
	@mkdir -p backups
	@pg_dump -h $(POSTGRES_HOST) -p $(POSTGRES_PORT) -U $(POSTGRES_USER) $(POSTGRES_DB) > backups/mpesa_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✓ Backup complete$(NC)"

# ============================================================================
# TESTING & QUALITY
# ============================================================================

test:
	@echo "$(BLUE)Running tests...$(NC)"
	@$(VENV_PYTHON) -m pytest tests/ -v

test-all: test

test-unit:
	@echo "$(BLUE)Running unit tests...$(NC)"
	@$(VENV_PYTHON) -m pytest tests -v --ignore=tests/e2e --ignore=tests/security --ignore=tests/load

test-integration:
	@echo "$(BLUE)Running integration tests...$(NC)"
	@$(VENV_PYTHON) -m pytest tests/test_integration.py -v

test-e2e:
	@echo "$(BLUE)Running end-to-end tests...$(NC)"
	@$(VENV_PYTHON) -m pytest tests/e2e -v

test-security:
	@echo "$(BLUE)Running security tests...$(NC)"
	@$(VENV_PYTHON) -m pytest tests/security -v

lint:
	@echo "$(BLUE)Running linting...$(NC)"
	@$(VENV_PYTHON) -m flake8 ingestion/ streaming/ schemas/ app/ analytics/ ml/ security/ tests/ --max-line-length=100
	@echo "$(GREEN)✓ Linting passed$(NC)"

format:
	@echo "$(BLUE)Formatting code...$(NC)"
	@$(VENV_PYTHON) -m black ingestion/ streaming/ schemas/ app/ analytics/ ml/ security/ tests/
	@echo "$(GREEN)✓ Code formatted$(NC)"

type-check:
	@echo "$(BLUE)Running type checks...$(NC)"
	@$(VENV_PYTHON) -m mypy ingestion/ streaming/ schemas/ app/ \
		--explicit-package-bases \
		--ignore-missing-imports \
		--disable-error-code=import-untyped \
		--no-error-summary

coverage:
	@echo "$(BLUE)Running coverage...$(NC)"
	@$(VENV_PYTHON) -m pytest tests/ --cov=ingestion --cov=streaming --cov=schemas --cov=app --cov-report=term-missing

# ============================================================================
# PRODUCTION & SECURITY
# ============================================================================

security-check:
	@echo "$(BLUE)Checking security policies...$(NC)"
	@$(VENV_PYTHON) security/gcp_integration.py

gcp-setup:
	@echo "$(BLUE)GCP Setup Instructions:$(NC)"
	@echo "  gcloud config set project mpesapipeline"
	@echo "  gcloud sql instances create mpesa-postgres --database-version=POSTGRES_15 --region=africa-south1"

build:
	@echo "$(BLUE)Building Docker image...$(NC)"
	@docker build -t mpesa-analytics:latest .
	@echo "$(GREEN)✓ Build complete$(NC)"

# ============================================================================
# MONITORING
# ============================================================================

health-check:
	@echo "$(BLUE)Running health checks...$(NC)"
	@curl -s http://localhost:5000/health || echo "Webhook not running"

logs:
	@tail -f logs/kafka_consumer.log 2>/dev/null || echo "No logs yet"

# ============================================================================
# UTILITIES
# ============================================================================

clean:
	@echo "$(YELLOW)Cleaning up...$(NC)"
	@find . -type d -name __pycache__ -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@rm -rf .pytest_cache .mypy_cache htmlcov .coverage
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

run-all:
	@echo "$(BLUE)Starting all components...$(NC)"
	@$(MAKE) infra-up
	@$(MAKE) grafana-up
	@echo ""
	@echo "$(GREEN)✓ All components running$(NC)"
	@echo ""
	@echo "Services:"
	@echo "  PostgreSQL:  $(POSTGRES_HOST):$(POSTGRES_PORT)"
	@echo "  Kafka:       localhost:9092"
	@echo "  Grafana:     http://localhost:3000"
	@echo ""
	@echo "Next: make ingest  (start data ingestion)"
