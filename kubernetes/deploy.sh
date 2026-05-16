#!/bin/bash
# kubernetes/deploy.sh - Deploy M-Pesa pipeline to Kubernetes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="mpesa-pipeline"
CONTEXT="${KUBE_CONTEXT:-}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
DRY_RUN="${DRY_RUN:-false}"

print_header() {
    echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   M-Pesa Streaming Pipeline - Kubernetes Deployment${NC}          ${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}\n"
}

print_section() {
    echo -e "\n${CYAN}▶ $1${NC}\n"
}

check_prerequisites() {
    print_section "Checking Prerequisites"
    
    local all_good=true
    
    # Check kubectl
    if command -v kubectl &> /dev/null; then
        local kubectl_version=$(kubectl version --client --short 2>/dev/null | awk '{print $3}')
        echo -e "${GREEN}✓${NC} kubectl ${kubectl_version}"
    else
        echo -e "${RED}✗${NC} kubectl not found (required)"
        all_good=false
    fi
    
    # Check kustomize
    if command -v kustomize &> /dev/null; then
        echo -e "${GREEN}✓${NC} kustomize"
    else
        echo -e "${YELLOW}⚠${NC} kustomize not found (required for deployment)"
        all_good=false
    fi
    
    # Check helm
    if command -v helm &> /dev/null; then
        local helm_version=$(helm version --short)
        echo -e "${GREEN}✓${NC} helm ${helm_version}"
    else
        echo -e "${YELLOW}⚠${NC} helm not found (optional)"
    fi
    
    # Check gcloud
    if command -v gcloud &> /dev/null; then
        echo -e "${GREEN}✓${NC} Google Cloud SDK"
    else
        echo -e "${YELLOW}⚠${NC} gcloud not found (optional for GKE)"
    fi
    
    if [ "$all_good" = false ]; then
        echo -e "\n${RED}Please install missing requirements${NC}"
        exit 1
    fi
}

setup_context() {
    print_section "Kubernetes Context Setup"
    
    local current_context=$(kubectl config current-context 2>/dev/null || echo "none")
    echo "Current context: ${CYAN}${current_context}${NC}"
    
    if [ -n "$CONTEXT" ]; then
        echo "Switching to context: $CONTEXT"
        kubectl config use-context "$CONTEXT"
    fi
    
    # Display cluster info
    local cluster_info=$(kubectl cluster-info 2>/dev/null | head -1)
    echo -e "Cluster: ${CYAN}${cluster_info}${NC}"
    
    # Check cluster access
    if kubectl cluster-info &> /dev/null; then
        echo -e "${GREEN}✓${NC} Cluster is accessible"
    else
        echo -e "${RED}✗${NC} Cannot access cluster"
        exit 1
    fi
}

create_namespace() {
    print_section "Creating Namespace"
    
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        echo -e "${YELLOW}⚠${NC} Namespace ${CYAN}${NAMESPACE}${NC} already exists"
    else
        echo "Creating namespace: $NAMESPACE"
        kubectl create namespace "$NAMESPACE"
        kubectl label namespace "$NAMESPACE" \
            environment="$ENVIRONMENT" \
            managed-by="kustomize"
        echo -e "${GREEN}✓${NC} Namespace created"
    fi
}

validate_manifests() {
    print_section "Validating Kubernetes Manifests"
    
    echo "Running: kubectl kustomize . --enable-alpha-plugins"
    if kustomize build . > /tmp/manifest-built.yaml 2>&1; then
        echo -e "${GREEN}✓${NC} Manifests are valid"
    else
        echo -e "${RED}✗${NC} Manifest validation failed"
        cat /tmp/manifest-built.yaml
        exit 1
    fi
    
    # Check manifest syntax
    echo "Running: kubectl apply --dry-run=client"
    if kubectl apply -f /tmp/manifest-built.yaml --dry-run=client &> /dev/null; then
        echo -e "${GREEN}✓${NC} Kubectl syntax check passed"
    else
        echo -e "${RED}✗${NC} Kubectl syntax check failed"
        exit 1
    fi
}

update_secrets() {
    print_section "Updating Secrets"
    
    echo "Secrets need to be updated manually. Run:"
    echo -e "  ${CYAN}kubectl create secret generic daraja-credentials \\${NC}"
    echo -e "    ${CYAN}--from-literal=api-key=YOUR_API_KEY \\${NC}"
    echo -e "    ${CYAN}--from-literal=api-secret=YOUR_API_SECRET \\${NC}"
    echo -e "    ${CYAN}-n $NAMESPACE${NC}"
    
    echo -e "\nPlaceholder values are in: ${CYAN}secrets.yaml${NC}"
    echo "Update with actual values from:"
    echo "  - GCP Secret Manager"
    echo "  - Terraform outputs"
    echo "  - Environment variables"
}

deploy_manifests() {
    print_section "Deploying Manifests"
    
    local cmd="kubectl apply -k . -n $NAMESPACE"
    if [ "$DRY_RUN" = "true" ]; then
        cmd="$cmd --dry-run=client"
        echo -e "${YELLOW}DRY RUN${NC} - No changes will be applied"
    fi
    
    echo "Running: $cmd"
    if eval "$cmd"; then
        echo -e "${GREEN}✓${NC} Manifests deployed successfully"
    else
        echo -e "${RED}✗${NC} Deployment failed"
        exit 1
    fi
}

wait_for_deployment() {
    print_section "Waiting for Deployments"
    
    local deployments=("webhook" "consumer" "processor")
    
    for deployment in "${deployments[@]}"; do
        echo "Waiting for ${CYAN}${deployment}${NC}..."
        if kubectl rollout status deployment/"mpesa-$deployment-$ENVIRONMENT" \
            -n "$NAMESPACE" \
            --timeout=5m; then
            echo -e "${GREEN}✓${NC} ${deployment} is ready"
        else
            echo -e "${RED}✗${NC} ${deployment} failed to become ready"
            kubectl describe deployment "mpesa-$deployment-$ENVIRONMENT" -n "$NAMESPACE"
        fi
    done
}

display_status() {
    print_section "Deployment Status"
    
    echo -e "${CYAN}Pods:${NC}"
    kubectl get pods -n "$NAMESPACE" -o wide
    
    echo -e "\n${CYAN}Services:${NC}"
    kubectl get svc -n "$NAMESPACE"
    
    echo -e "\n${CYAN}Ingress:${NC}"
    kubectl get ingress -n "$NAMESPACE"
    
    echo -e "\n${CYAN}PersistentVolumeClaims:${NC}"
    kubectl get pvc -n "$NAMESPACE"
}

show_endpoints() {
    print_section "Service Endpoints"
    
    local webhook_svc=$(kubectl get service webhook -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
    echo -e "Webhook Service: ${CYAN}${webhook_svc}${NC}"
    
    echo -e "\n${CYAN}Port Forward Commands:${NC}"
    echo "  kubectl port-forward -n $NAMESPACE svc/webhook 8080:8080"
    echo "  kubectl port-forward -n $NAMESPACE svc/consumer 8080:8080"
    echo "  kubectl port-forward -n $NAMESPACE svc/processor 8080:8080"
}

check_logs() {
    print_section "Recent Logs"
    
    echo -e "${CYAN}Webhook logs:${NC}"
    kubectl logs -n "$NAMESPACE" -l app=webhook --tail=10 --timestamps=true 2>/dev/null || echo "No logs available"
    
    echo -e "\n${CYAN}Consumer logs:${NC}"
    kubectl logs -n "$NAMESPACE" -l app=consumer --tail=10 --timestamps=true 2>/dev/null || echo "No logs available"
}

verify_deployment() {
    print_section "Verifying Deployment"
    
    # Check if all deployments are ready
    local webhook_ready=$(kubectl get deployment mpesa-webhook-"$ENVIRONMENT" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
    local consumer_ready=$(kubectl get deployment mpesa-consumer-"$ENVIRONMENT" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
    local processor_ready=$(kubectl get deployment mpesa-processor-"$ENVIRONMENT" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
    
    echo "Ready Replicas:"
    echo "  Webhook: $webhook_ready/2"
    echo "  Consumer: $consumer_ready/2"
    echo "  Processor: $processor_ready/2"
    
    if [ "$webhook_ready" -ge 1 ] && [ "$consumer_ready" -ge 1 ] && [ "$processor_ready" -ge 1 ]; then
        echo -e "\n${GREEN}✓${NC} Deployment verified successfully"
        return 0
    else
        echo -e "\n${YELLOW}⚠${NC} Some pods are not ready yet"
        return 1
    fi
}

main() {
    print_header
    
    check_prerequisites
    setup_context
    create_namespace
    validate_manifests
    update_secrets
    deploy_manifests
    
    if [ "$DRY_RUN" != "true" ]; then
        echo -e "\n${YELLOW}Waiting for pods to be ready...${NC}"
        sleep 10
        wait_for_deployment
        display_status
        show_endpoints
        check_logs
        verify_deployment
    fi
    
    echo -e "\n${GREEN}✓ Deployment complete!${NC}\n"
}

# Run main function
main "$@"
