#!/bin/bash
# terraform/setup.sh - Interactive setup script for Terraform deployment
# Usage: ./terraform/setup.sh

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Spinner function
spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

clear_screen() {
    clear
}

print_header() {
    echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║    M-Pesa Streaming Pipeline - Terraform Setup${NC}               ${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}\n"
}

print_section() {
    echo -e "\n${CYAN}▶ $1${NC}\n"
}

check_requirements() {
    print_section "Checking Prerequisites"
    
    local all_good=true
    
    # Check Terraform
    if command -v terraform &> /dev/null; then
        local tf_version=$(terraform version -json 2>/dev/null | jq -r '.terraform_version')
        echo -e "${GREEN}✓${NC} Terraform ${tf_version}"
    else
        echo -e "${RED}✗${NC} Terraform not found (required)"
        echo "  Install from: https://www.terraform.io/downloads"
        all_good=false
    fi
    
    # Check gcloud
    if command -v gcloud &> /dev/null; then
        echo -e "${GREEN}✓${NC} Google Cloud SDK"
    else
        echo -e "${RED}✗${NC} Google Cloud SDK not found (required)"
        echo "  Install from: https://cloud.google.com/sdk/docs/install"
        all_good=false
    fi
    
    # Check jq
    if command -v jq &> /dev/null; then
        echo -e "${GREEN}✓${NC} jq (JSON processor)"
    else
        echo -e "${YELLOW}⚠${NC} jq not found (optional, some features disabled)"
    fi
    
    # Check tfsec
    if command -v tfsec &> /dev/null; then
        echo -e "${GREEN}✓${NC} tfsec (security scanner)"
    else
        echo -e "${YELLOW}⚠${NC} tfsec not found (optional, skipping security checks)"
    fi
    
    if [ "$all_good" = false ]; then
        echo -e "\n${RED}Please install missing requirements and try again${NC}"
        exit 1
    fi
}

setup_gcp() {
    print_section "Google Cloud Project Setup"
    
    echo "This script will help you set up your GCP project."
    echo -e "Current GCP project: ${CYAN}$(gcloud config get-value project)${NC}\n"
    
    read -p "Do you want to use the current project? (y/n) " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "\n${YELLOW}List of projects:${NC}"
        gcloud projects list --format="table(projectId,name,status)"
        read -p "Enter project ID: " PROJECT_ID
        gcloud config set project "$PROJECT_ID"
    fi
    
    PROJECT_ID=$(gcloud config get-value project)
    export GCP_PROJECT_ID="$PROJECT_ID"
    
    # Check billing
    echo -e "\n${YELLOW}Checking billing...${NC}"
    if gcloud billing projects describe "$PROJECT_ID" &> /dev/null; then
        echo -e "${GREEN}✓${NC} Billing is enabled"
    else
        echo -e "${RED}✗${NC} Billing is not enabled"
        echo "  Enable it at: https://console.cloud.google.com/billing"
        exit 1
    fi
}

configure_variables() {
    print_section "Configuration Setup"
    
    if [ -f "terraform/terraform.tfvars" ]; then
        echo -e "${YELLOW}terraform.tfvars already exists${NC}"
        read -p "Do you want to recreate it? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return
        fi
    fi
    
    echo "Enter configuration values:\n"
    
    # Environment
    echo -e "${CYAN}Environment:${NC} (dev/staging/prod)"
    read -p "Enter environment [dev]: " ENVIRONMENT
    ENVIRONMENT="${ENVIRONMENT:-dev}"
    
    # Region
    echo -e "\n${CYAN}Region:${NC} (us-central1, us-east1, europe-west1, asia-east1)"
    read -p "Enter region [us-central1]: " REGION
    REGION="${REGION:-us-central1}"
    
    # Alert email
    echo -e "\n${CYAN}Alert Email:${NC} (for monitoring alerts)"
    read -p "Enter email address: " ALERT_EMAIL
    
    # Passwords (with input masking)
    echo -e "\n${CYAN}Database Passwords:${NC}"
    echo -n "Enter Cloud SQL root password: "
    read -s ROOT_PASSWORD
    echo
    
    echo -n "Enter Cloud SQL app user password: "
    read -s APP_PASSWORD
    echo
    
    # Generate terraform.tfvars
    cat > terraform/terraform.tfvars << EOF
# M-Pesa Streaming Pipeline - Terraform Configuration
# Generated: $(date)

gcp_project_id = "$GCP_PROJECT_ID"
gcp_region     = "$REGION"
environment    = "$ENVIRONMENT"
alert_email    = "$ALERT_EMAIL"

cloud_sql_root_password     = "$ROOT_PASSWORD"
cloud_sql_app_user_password = "$APP_PASSWORD"

# Additional configurations (use defaults or customize)
project_name       = "mpesa-streaming"
project_short_name = "mps"

cloud_run_min_instances = 1
cloud_run_max_instances = $([ "$ENVIRONMENT" = "prod" ] && echo "10" || echo "3")

enable_monitoring = true
enable_logging    = true
EOF
    
    echo -e "\n${GREEN}✓${NC} Configuration saved to terraform/terraform.tfvars"
}

initialize_terraform() {
    print_section "Initializing Terraform"
    
    cd terraform
    
    echo "Running: terraform init -upgrade"
    terraform init -upgrade &
    spinner $!
    
    echo -e "${GREEN}✓${NC} Terraform initialized"
    
    cd ..
}

validate_configuration() {
    print_section "Validating Configuration"
    
    cd terraform
    
    echo "Running: terraform validate"
    if terraform validate &> /dev/null; then
        echo -e "${GREEN}✓${NC} Configuration is valid"
    else
        echo -e "${RED}✗${NC} Configuration validation failed"
        terraform validate
        cd ..
        exit 1
    fi
    
    echo "Running: terraform fmt -check"
    if terraform fmt -check -recursive . &> /dev/null; then
        echo -e "${GREEN}✓${NC} Formatting is correct"
    else
        echo -e "${YELLOW}⚠${NC} Formatting issues found"
        read -p "Fix formatting automatically? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            terraform fmt -recursive .
            echo -e "${GREEN}✓${NC} Formatting fixed"
        fi
    fi
    
    cd ..
}

generate_plan() {
    print_section "Generating Terraform Plan"
    
    cd terraform
    
    echo "Running: terraform plan"
    if terraform plan -out=tfplan -lock=false > plan.log 2>&1; then
        echo -e "${GREEN}✓${NC} Plan generated successfully"
        
        # Count resources
        local resource_count=$(terraform show -json tfplan 2>/dev/null | jq '.resource_changes | length' || echo "?")
        echo -e "\nResources to create/modify: ${CYAN}${resource_count}${NC}"
        
        read -p "View detailed plan? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            terraform show tfplan | head -100
            echo "... (use 'terraform show tfplan' for full plan)"
        fi
    else
        echo -e "${RED}✗${NC} Plan generation failed"
        cat plan.log
        cd ..
        exit 1
    fi
    
    cd ..
}

confirm_deployment() {
    print_section "Deployment Confirmation"
    
    echo -e "${YELLOW}⚠  WARNING: This will create cloud resources and may incur costs!${NC}\n"
    echo "Please review the plan above before proceeding."
    echo -e "\nEstimated monthly cost: \$100-500 (varies by usage)\n"
    
    read -p "Do you want to proceed with deployment? (type 'yes' to confirm): " confirmation
    
    if [ "$confirmation" != "yes" ]; then
        echo -e "\n${YELLOW}Deployment cancelled${NC}"
        exit 0
    fi
}

apply_configuration() {
    print_section "Applying Configuration"
    
    cd terraform
    
    echo "Running: terraform apply"
    if terraform apply tfplan; then
        echo -e "\n${GREEN}✓${NC} Deployment completed successfully!"
        
        # Save outputs
        echo -e "\n${CYAN}Saving outputs...${NC}"
        terraform output > ../deployment-outputs.json
        terraform output -json > ../deployment-outputs.json.raw
        
        echo -e "${GREEN}✓${NC} Outputs saved to deployment-outputs.json\n"
        
        # Display key outputs
        echo -e "${CYAN}Key Endpoints:${NC}"
        echo "  Webhook URL: $(terraform output -raw webhook_endpoint)"
        echo "  Cloud SQL: $(terraform output -json cloud_sql_info | jq -r '.instance_name')"
        echo "  BigQuery: $(terraform output -json bigquery_info | jq -r '.raw_dataset')"
        
    else
        echo -e "${RED}✗${NC} Deployment failed"
        cd ..
        exit 1
    fi
    
    cd ..
}

post_deployment() {
    print_section "Post-Deployment Steps"
    
    cat << 'EOF'
1. UPDATE SECRETS IN SECRET MANAGER:
   gcloud secrets versions add "mps-dev-daraja-api-key" --data-file=- <<< "YOUR_API_KEY"
   gcloud secrets versions add "mps-dev-daraja-api-secret" --data-file=- <<< "YOUR_API_SECRET"
   gcloud secrets versions add "mps-dev-webhook-signing-key" --data-file=- <<< "YOUR_SIGNING_KEY"

2. BUILD & PUSH DOCKER IMAGES:
   docker build -t us-central1-docker.pkg.dev/PROJECT_ID/mpesa-docker/webhook:latest ./ingestion
   docker push us-central1-docker.pkg.dev/PROJECT_ID/mpesa-docker/webhook:latest

3. INITIALIZE DATABASE:
   gcloud sql connect mps-dev-postgres --user=mpesa_app --database=mpesa_dev < scripts/schema.sql

4. CONFIGURE SAFARICOM DARAJA WEBHOOKS:
   - Login to: https://console.safaricom.co.ke/
   - Set C2B callback: https://YOUR_WEBHOOK_URL/webhook/c2b
   - Set B2C result: https://YOUR_WEBHOOK_URL/webhook/b2c

5. TEST DEPLOYMENT:
   curl -X GET https://YOUR_WEBHOOK_URL/health
   gcloud pubsub subscriptions pull mps-dev-mpesa-transactions-sub --limit=5

6. MONITOR:
   - Cloud Console: https://console.cloud.google.com/
   - BigQuery: Check raw_mpesa_dev.mpesa_raw_transactions
   - Logs: gcloud logs read --project=YOUR_PROJECT_ID --limit=50

7. DOCUMENTATION:
   - Review: terraform/deployment-outputs.json
   - Docs: terraform/README.md
   - Troubleshoot: docs/TROUBLESHOOTING.md
EOF

    echo
}

main() {
    clear_screen
    print_header
    
    echo -e "${YELLOW}This interactive script will guide you through the setup process.${NC}\n"
    
    # Run setup steps
    check_requirements
    setup_gcp
    configure_variables
    initialize_terraform
    validate_configuration
    generate_plan
    confirm_deployment
    apply_configuration
    post_deployment
    
    echo -e "\n${GREEN}✓ Setup complete!${NC}\n"
    echo "Next steps:"
    echo "  1. Follow the post-deployment steps above"
    echo "  2. Monitor deployment: gcloud run services list"
    echo "  3. View logs: gcloud logs read --limit=50"
    echo "  4. Check dashboard: gcloud monitoring dashboards list"
    echo
}

# Run main function
main "$@"
