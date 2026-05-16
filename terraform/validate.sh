#!/bin/bash
# terraform/validate.sh - Terraform validation and security checks
# Usage: ./terraform/validate.sh [dev|staging|prod]

set -e

ENVIRONMENT="${1:-dev}"
PROJECT_ID="${GCP_PROJECT_ID:-}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Terraform Validation for M-Pesa Streaming Pipeline ===${NC}\n"

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v terraform &> /dev/null; then
    echo -e "${RED}✗ Terraform not found. Please install terraform v1.0+${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Terraform found: $(terraform version -json | jq -r '.terraform_version')${NC}"

if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}✗ gcloud CLI not found. Please install Google Cloud SDK${NC}"
    exit 1
fi
echo -e "${GREEN}✓ gcloud CLI found${NC}"

if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}⚠ jq not found. Some features may not work${NC}"
fi

# Check GCP project
if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID=$(gcloud config get-value project)
fi

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}✗ GCP_PROJECT_ID not set and no default project configured${NC}"
    echo "Set with: export GCP_PROJECT_ID=your-project-id"
    exit 1
fi
echo -e "${GREEN}✓ GCP Project: $PROJECT_ID${NC}"

# Check terraform variables file
echo -e "\n${YELLOW}Checking Terraform configuration...${NC}"

if [ ! -f "terraform/terraform.tfvars" ]; then
    echo -e "${RED}✗ terraform/terraform.tfvars not found${NC}"
    echo "Create from template: cp terraform/terraform.tfvars.example terraform/terraform.tfvars"
    exit 1
fi
echo -e "${GREEN}✓ terraform.tfvars found${NC}"

# Verify required variables
echo -e "\n${YELLOW}Validating required variables...${NC}"

REQUIRED_VARS=(
    "gcp_project_id"
    "gcp_region"
    "environment"
    "alert_email"
    "cloud_sql_root_password"
    "cloud_sql_app_user_password"
)

MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${var}" terraform/terraform.tfvars; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "${RED}✗ Missing required variables:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    exit 1
fi
echo -e "${GREEN}✓ All required variables present${NC}"

# Initialize Terraform
echo -e "\n${YELLOW}Initializing Terraform...${NC}"

cd terraform
terraform init -upgrade

# Validate configuration
echo -e "\n${YELLOW}Validating Terraform configuration...${NC}"

if terraform validate; then
    echo -e "${GREEN}✓ Configuration is valid${NC}"
else
    echo -e "${RED}✗ Configuration validation failed${NC}"
    exit 1
fi

# Format check
echo -e "\n${YELLOW}Checking Terraform formatting...${NC}"

if terraform fmt -check -recursive .; then
    echo -e "${GREEN}✓ Formatting is correct${NC}"
else
    echo -e "${YELLOW}⚠ Formatting issues found. Running terraform fmt...${NC}"
    terraform fmt -recursive .
    echo -e "${YELLOW}Fixed formatting issues. Please review and commit changes.${NC}"
fi

# Security checks with tfsec (if available)
if command -v tfsec &> /dev/null; then
    echo -e "\n${YELLOW}Running security checks (tfsec)...${NC}"
    
    if tfsec . -f json > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Security checks passed${NC}"
    else
        echo -e "${YELLOW}⚠ Security issues found (review recommended):${NC}"
        tfsec . --format compact || true
    fi
else
    echo -e "${YELLOW}⚠ tfsec not found. Skipping security checks.${NC}"
    echo "Install: brew install tfsec"
fi

# Plan generation
echo -e "\n${YELLOW}Generating Terraform plan for review...${NC}"

if terraform plan -out=tfplan -lock=false > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Plan generated successfully${NC}"
    
    # Show plan summary
    echo -e "\n${BLUE}=== Plan Summary ===${NC}"
    terraform show -json tfplan | jq -r '.resource_changes[] | select(.type != "google_project_service") | "\(.change.actions[0]) \(.type) \(.address)"' || true
    
else
    echo -e "${RED}✗ Plan generation failed${NC}"
    exit 1
fi

cd ..

# Summary
echo -e "\n${BLUE}=== Validation Complete ===${NC}"
echo -e "${GREEN}✓ Terraform configuration is ready for deployment${NC}"
echo -e "\nNext steps:"
echo "  1. Review the plan: cd terraform && terraform show tfplan"
echo "  2. Apply configuration: terraform apply tfplan"
echo "  3. Save outputs: terraform output > deployment-outputs.json"

# Return to initial directory
exit 0
