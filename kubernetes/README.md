# Kubernetes Deployment Guide - M-Pesa Streaming Pipeline

## Overview

This directory contains complete Kubernetes manifests for deploying the M-Pesa Real-Time Transaction Streaming Pipeline. The manifests are organized using Kustomize for environment-specific customization.

## 📁 File Structure

```
kubernetes/
├── namespace.yaml                # Namespace definition
├── rbac.yaml                     # ServiceAccounts, Roles, RoleBindings
├── configmap.yaml                # Configuration maps & init scripts
├── secrets.yaml                  # Secrets (with placeholders)
├── services.yaml                 # Service definitions
├── webhook-deployment.yaml        # Webhook service deployment
├── consumer-deployment.yaml       # Consumer service deployment
├── processor-deployment.yaml      # Processor service deployment
├── ingress.yaml                  # Ingress & TLS configuration
├── network-policy.yaml           # Network access policies
├── persistent-volumes.yaml       # Storage configuration
├── monitoring.yaml               # Prometheus, Grafana, alerts
├── resource-management.yaml      # Quotas, limits, policies
├── kustomization.yaml            # Kustomize base configuration
├── deploy.sh                     # Deployment script
└── README.md                     # This file
```

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Install required tools
- kubectl (1.24+)
- kustomize (5.0+)
- helm (3.0+) - optional
- gcloud CLI - for GKE
```

### 2. Set Environment Variables

```bash
export ENVIRONMENT=dev          # dev/staging/prod
export GCP_PROJECT_ID=xxx       # Your GCP project
export GCP_REGION=us-central1
export DARAJA_API_KEY=xxx
export DARAJA_API_SECRET=xxx
export CLOUD_SQL_APP_PASSWORD=xxx
export CLOUD_SQL_HOST=xxx       # From Terraform output
```

### 3. Deploy to Kubernetes

```bash
cd kubernetes

# Validate manifests
kustomize build . | kubectl apply -f - --dry-run=client

# Deploy
bash deploy.sh

# Or manual deployment
kubectl kustomize . | kubectl apply -f -
```

### 4. Verify Deployment

```bash
# Check pods
kubectl get pods -n mpesa-pipeline

# Check services
kubectl get svc -n mpesa-pipeline

# Check ingress
kubectl get ingress -n mpesa-pipeline

# View logs
kubectl logs -f -n mpesa-pipeline -l app=webhook
```

## 🏗️ Architecture

### Services

1. **Webhook (Ingestion)**
   - Receives Daraja API callbacks
   - Publishes to Pub/Sub
   - Replicas: 2-10 (autoscaled)
   - Memory: 256Mi-512Mi
   - CPU: 200m-500m

2. **Consumer (Streaming)**
   - Subscribes to Pub/Sub
   - Processes & enriches messages
   - Writes to BigQuery
   - Replicas: 2-5 (autoscaled)
   - Memory: 512Mi-1Gi
   - CPU: 250m-1000m

3. **Processor (Analytics)**
   - Aggregates enriched data
   - Computes metrics
   - Updates analytics tables
   - Replicas: 2-8 (autoscaled)
   - Memory: 1Gi-2Gi
   - CPU: 500m-2000m

### Data Flow

```
Daraja API
    ↓
Webhook (Cloud Run / K8s)
    ↓ (Pub/Sub)
Consumer (K8s)
    ↓ (BigQuery)
Data Warehouse
    ↓
Processor (K8s)
    ↓ (Analytics)
BigQuery Analytics Tables
    ↓
dbt Transformations
    ↓
Dashboards & Reports
```

## 🔐 Security

### RBAC (Role-Based Access Control)

- **webhook-sa**: Pub/Sub publisher, BigQuery writer, secret reader
- **consumer-sa**: Pub/Sub subscriber, BigQuery writer, secret reader
- **processor-sa**: Pub/Sub subscriber, BigQuery writer, secret reader

### Network Policies

- Deny all ingress by default
- Allow only necessary pod-to-pod communication
- Allow ingress from ingress-nginx only
- Restrict egress to specific ports/protocols

### Secrets Management

Secrets are stored in Kubernetes Secret resources with:
- RBAC access control
- Audit logging
- Encryption at rest (KMS)
- Automatic rotation (via Secret Manager)

## 📊 Monitoring & Observability

### Prometheus ServiceMonitor

```bash
# Metrics are scrapped from:
- /metrics port (8888) on each pod
- 30-second intervals
- ServiceMonitor resources for Prometheus Operator
```

### Alert Rules

Pre-configured alerts for:
- High error rates (>5%)
- Consumer lag (>1000 messages)
- High CPU usage (>80%)
- Pod crashes
- PVC usage (>80%)

### Grafana Dashboard

Dashboard available at:
- Transaction volume
- Error rates
- Consumer lag
- Processing latency
- Pod resource usage

## 🔄 Deployment Strategies

### Rolling Update

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
```

- Ensures zero downtime
- One extra pod during update
- New version becomes available gradually

### Blue-Green Deployment

For production, use:
```bash
# Deploy new version to blue environment
kubectl set image deployment/webhook webhook=new:v2 -n mpesa-pipeline

# Test blue environment
kubectl port-forward svc/webhook 8080:8080

# Switch traffic
kubectl patch service webhook -p '{"spec":{"selector":{"version":"v2"}}}'

# Keep green for rollback
```

### Canary Deployment

Use Flagger for automatic canary deployments:
```bash
helm install flagger flagger/flagger --namespace=istio-system
```

## 📈 Autoscaling

### Horizontal Pod Autoscaler (HPA)

Each deployment has HPA configured:

```yaml
minReplicas: 2
maxReplicas: 10
targetCPU: 70-80%
targetMemory: 75-85%
```

### Manual Scaling

```bash
# Scale webhook to 5 replicas
kubectl scale deployment webhook -n mpesa-pipeline --replicas=5

# Check current replicas
kubectl get deployment webhook -n mpesa-pipeline
```

## 🔧 Troubleshooting

### Pods Not Running

```bash
# Check pod status
kubectl describe pod <pod-name> -n mpesa-pipeline

# View events
kubectl get events -n mpesa-pipeline --sort-by='.lastTimestamp'

# Check logs
kubectl logs <pod-name> -n mpesa-pipeline
```

### Service Not Accessible

```bash
# Check service endpoints
kubectl get endpoints -n mpesa-pipeline

# Port forward for testing
kubectl port-forward svc/webhook 8080:8080 -n mpesa-pipeline

# Test endpoint
curl http://localhost:8080/health
```

### Database Connection Issues

```bash
# Test database connectivity
kubectl run -it --rm debug --image=google/cloud-sdk:latest --restart=Never \
  -- gcloud sql connect mps-dev-postgres --user=mpesa_app

# Check Secret
kubectl get secret db-credentials -n mpesa-pipeline -o yaml
```

### High Memory Usage

```bash
# Check memory usage
kubectl top pods -n mpesa-pipeline

# Increase limits in persistent-volumes.yaml
# Apply changes
kubectl apply -f persistent-volumes.yaml
```

## 🔄 Common Tasks

### Update Configuration

```bash
# Edit ConfigMap
kubectl edit cm mpesa-config -n mpesa-pipeline

# Or apply new values
kubectl create configmap mpesa-config --from-file=config/ --dry-run=client -o yaml | \
  kubectl apply -f -
```

### Update Secrets

```bash
# Update single secret
kubectl create secret generic daraja-credentials \
  --from-literal=api-key=NEW_KEY \
  --from-literal=api-secret=NEW_SECRET \
  -n mpesa-pipeline \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart pods to pick up new secrets
kubectl rollout restart deployment/webhook -n mpesa-pipeline
```

### View Logs

```bash
# All logs
kubectl logs -f -n mpesa-pipeline -l app=webhook

# Specific pod
kubectl logs -f <pod-name> -n mpesa-pipeline

# Last 100 lines with timestamps
kubectl logs -n mpesa-pipeline -l app=webhook --tail=100 --timestamps=true
```

### Execute Commands in Pod

```bash
# Interactive shell
kubectl exec -it <pod-name> -n mpesa-pipeline -- /bin/sh

# Run single command
kubectl exec <pod-name> -n mpesa-pipeline -- python --version
```

### Port Forward

```bash
# Forward local port 8080 to pod port 8080
kubectl port-forward svc/webhook 8080:8080 -n mpesa-pipeline

# Test local endpoint
curl http://localhost:8080/health
```

## 🚨 Disaster Recovery

### Backup Strategy

```bash
# Backup namespace
kubectl get all -n mpesa-pipeline -o yaml > backup-$(date +%s).yaml

# Backup specific resource
kubectl get deployment webhook -n mpesa-pipeline -o yaml > webhook-backup.yaml
```

### Restore Strategy

```bash
# Restore from backup
kubectl apply -f backup-*.yaml

# Rollback deployment
kubectl rollout undo deployment/webhook -n mpesa-pipeline
kubectl rollout history deployment/webhook -n mpesa-pipeline
```

### Database Backup (Cloud SQL)

```bash
# Create on-demand backup
gcloud sql backups create \
  --instance=mps-dev-postgres \
  --description="Before upgrade"

# List backups
gcloud sql backups list --instance=mps-dev-postgres

# Restore from backup
gcloud sql restore-backup mps-dev-postgres \
  --backup-id=<BACKUP_ID>
```

## 📦 Integration with CI/CD

### GitHub Actions

```yaml
name: Deploy to K8s
on: [push]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy
        run: |
          kubectl kustomize kubernetes | kubectl apply -f -
```

### Cloud Build

```yaml
steps:
  - name: Deploy
    args: ['kustomize', 'build', 'kubernetes']
  - name: Verify
    args: ['kubectl', 'rollout', 'status', 'deployment/webhook']
```

## 🎓 Best Practices

1. **Always use namespaces** to isolate environments
2. **Set resource requests/limits** for predictable scheduling
3. **Use health checks** (liveness/readiness probes)
4. **Enable pod disruption budgets** for high availability
5. **Use network policies** for security
6. **Enable audit logging** for compliance
7. **Monitor resource usage** and autoscale
8. **Regular backups** of configurations and data
9. **Use GitOps** to manage configurations
10. **Test disaster recovery** regularly

## 📋 Pre-Deployment Checklist

- [ ] kubectl configured and authenticated
- [ ] Cluster has minimum 3 nodes (for production)
- [ ] Persistent volumes available (min 100Gi)
- [ ] Namespace created
- [ ] Secrets populated (not placeholders)
- [ ] ConfigMaps validated
- [ ] Network policies reviewed
- [ ] Resource quotas set
- [ ] Monitoring configured
- [ ] Ingress DNS configured
- [ ] TLS certificates ready
- [ ] Database accessible
- [ ] Pub/Sub topics/subscriptions created

## 🔗 Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kustomize Guide](https://kustomize.io/)
- [GKE Best Practices](https://cloud.google.com/kubernetes-engine/docs/best-practices)
- [Prometheus Operator](https://prometheus-operator.dev/)
- [Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)

## 📞 Support

For issues or questions:
1. Check logs: `kubectl logs -f <pod-name>`
2. Describe pod: `kubectl describe pod <pod-name>`
3. Check events: `kubectl get events --sort-by='.lastTimestamp'`
4. Review deployment guide
5. Check cloud provider documentation

---

**Status:** Production Ready  
**Version:** 1.0.0  
**Last Updated:** May 2026
