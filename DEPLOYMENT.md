# A2A Registry - ClusterKit Deployment Guide

This guide covers deploying A2A Registry to ClusterKit (GKE Autopilot) at `a2aregistry.org`.

## Architecture

- **Namespace**: `a2aregistry`
- **Domain**: `a2aregistry.org`
- **Database**: `a2a_registry_beta` in shared Cloud SQL instance `clusterkit-db`
- **Gateway**: Shared ClusterKit Gateway (34.149.49.202) in `torale` namespace
- **HTTPRoute**: Cross-namespace routing from `torale` → `a2aregistry`

## Prerequisites

1. ClusterKit Terraform applied (SSL cert, Gateway, ReferenceGrants)
2. Database created in Cloud SQL
3. Workload Identity configured
4. Secrets created in Kubernetes

## Initial Setup

### 1. Apply ClusterKit Terraform

```bash
cd ../clusterkit/terraform

# Apply root Terraform (SSL cert + Gateway)
terraform plan -var="project_id=baldmaninc"
terraform apply -var="project_id=baldmaninc"

# Apply Torale project Terraform (database + Workload Identity)
cd projects/torale
terraform plan
terraform apply
```

This creates:
- SSL certificate for `a2aregistry.org`
- ReferenceGrant allowing HTTPRoute → Service across namespaces
- Database `a2a_registry_beta` in Cloud SQL
- Workload Identity binding for `a2aregistry-sa`

### 2. Create Kubernetes Secrets

```bash
# Connect to cluster
gcloud container clusters get-credentials clusterkit --region us-central1 --project baldmaninc

# Create namespace
kubectl create namespace a2aregistry

# Create secrets
kubectl create secret generic a2aregistry-secrets -n a2aregistry \
  --from-literal=DB_PASSWORD="<your-secure-password>" \
  --from-literal=POSTHOG_API_KEY="" \
  --from-literal=SECRET_KEY="<random-secret-key>"
```

### 3. Deploy with Helm

```bash
# Install/upgrade deployment
helm upgrade --install a2aregistry ./helm/a2aregistry \
  --namespace a2aregistry \
  --values ./helm/a2aregistry/values-prod.yaml \
  --set image.tag=latest \
  --wait \
  --timeout 5m
```

### 4. Verify Deployment

```bash
# Check deployments
kubectl get deployments -n a2aregistry
kubectl get pods -n a2aregistry

# Check services
kubectl get svc -n a2aregistry

# Check HTTPRoute (in torale namespace!)
kubectl get httproute -n torale | grep a2aregistry
kubectl describe httproute a2aregistry-beta -n torale

# Check Gateway status
kubectl get gateway clusterkit-gateway -n torale
kubectl describe gateway clusterkit-gateway -n torale

# Check SSL certificate
gcloud compute ssl-certificates describe a2aregistry-beta-cert

# Verify DNS
dig +short a2aregistry.org @1.1.1.1
# Should return: 34.149.49.202

# Test endpoints
curl https://a2aregistry.org/health  # Frontend health
curl https://a2aregistry.org/api/health  # API health
```

## CI/CD

GitHub Actions automatically deploys on push to `main`:

1. Builds 3 container images (api, worker, frontend)
2. Pushes to GCR: `gcr.io/baldmaninc/a2a-registry-*`
3. Deploys with Helm using commit SHA as image tag

Workflow: `.github/workflows/deploy-backend.yml`

## Manual Deployment

```bash
# Build images locally
docker build -t gcr.io/baldmaninc/a2a-registry-api:dev backend/
docker build -t gcr.io/baldmaninc/a2a-registry-worker:dev backend/
docker build -t gcr.io/baldmaninc/a2a-registry-frontend:dev \
  --build-arg VITE_API_URL=https://a2aregistry.org/api \
  website/

# Push images
docker push gcr.io/baldmaninc/a2a-registry-api:dev
docker push gcr.io/baldmaninc/a2a-registry-worker:dev
docker push gcr.io/baldmaninc/a2a-registry-frontend:dev

# Deploy
helm upgrade --install a2aregistry ./helm/a2aregistry \
  --namespace a2aregistry \
  --values ./helm/a2aregistry/values-prod.yaml \
  --set image.tag=dev
```

## Database Migrations

Run migrations after deployment:

```bash
# Port-forward to API pod
kubectl port-forward -n a2aregistry deployment/a2aregistry-api 8000:8000

# Run migration script (if needed)
# Or use Cloud SQL proxy locally:
cloud-sql-proxy baldmaninc:us-central1:clusterkit-db &
psql -h 127.0.0.1 -U a2a_registry_beta -d a2a_registry_beta < backend/migrations/versions/001_initial_schema.sql
```

## Troubleshooting

### HTTPRoute not working

Check that:
1. HTTPRoute is in `torale` namespace (same as Gateway)
2. ReferenceGrant exists for cross-namespace routing
3. Annotation `cloudflare-proxied: "false"` is present

```bash
kubectl describe httproute a2aregistry-beta -n torale
kubectl get referencegrant -n a2aregistry
```

### SSL certificate not provisioning

Google-managed certs take ~15 minutes:

```bash
gcloud compute ssl-certificates describe a2aregistry-beta-cert
# Status should be ACTIVE
```

### DNS not resolving

Check ExternalDNS logs:

```bash
kubectl logs -n external-dns -l app.kubernetes.io/name=external-dns
```

Verify Cloudflare DNS is set to "DNS only" (gray cloud), not "Proxied" (orange cloud).

### Database connection failing

Check Cloud SQL proxy sidecar:

```bash
kubectl logs -n a2aregistry deployment/a2aregistry-api -c cloud-sql-proxy
kubectl logs -n a2aregistry deployment/a2aregistry-api -c api
```

Verify Workload Identity:

```bash
kubectl describe sa a2aregistry-sa -n a2aregistry
# Should have annotation: iam.gke.io/gcp-service-account
```

## Costs

Estimated monthly cost for beta deployment:
- GKE pods (Spot): ~£3-5/month
- Cloud SQL (shared): Included in Torale cost
- Load balancer (shared Gateway): Included in ClusterKit cost
- **Total incremental cost**: ~£3-5/month

## Scaling

Configured autoscaling:
- API: 2-5 pods (target 70% CPU)
- Frontend: 2-3 pods (target 70% CPU)
- Worker: 1 pod (no autoscaling)

All pods use Spot instances for 60-91% cost savings.
