# Kubernetes Deployment

Kubernetes manifests for deploying the A2A Registry backend to your cluster.

## Prerequisites

- Kubernetes cluster (tested with 1.28+)
- `kubectl` configured
- PostgreSQL database (can be in-cluster or external)
- Ingress controller (e.g., nginx-ingress)
- cert-manager for TLS (optional)

## Setup

### 1. Create secrets

```bash
cp secrets.yaml.example secrets.yaml
# Edit secrets.yaml with real values
kubectl apply -f secrets.yaml
```

### 2. Build and push Docker image

```bash
cd ../backend
docker build -t your-registry/a2a-registry-backend:latest .
docker push your-registry/a2a-registry-backend:latest
```

Update `deployment.yaml` and `worker.yaml` with your image registry.

### 3. Deploy

```bash
kubectl apply -f deployment.yaml
kubectl apply -f worker.yaml
kubectl apply -f ingress.yaml
```

### 4. Verify deployment

```bash
kubectl get pods -l app=a2a-registry
kubectl logs -l app=a2a-registry,component=api
kubectl logs -l app=a2a-registry,component=worker
```

### 5. Run initial migration

```bash
# Port-forward to API
kubectl port-forward svc/a2a-registry-api 8000:80

# In another terminal, run migration
cd ..
DATABASE_URL="postgresql://..." uv run python scripts/sync_to_db.py
```

## Components

- **deployment.yaml** - API server (2 replicas)
- **worker.yaml** - Health check worker (1 replica)
- **ingress.yaml** - Ingress for external access
- **secrets.yaml** - Sensitive configuration (not committed)

## Scaling

Scale API replicas:
```bash
kubectl scale deployment a2a-registry-api --replicas=3
```

Worker should typically run as single replica (health checks are distributed across all agents).

## Monitoring

Check health:
```bash
kubectl get pods
kubectl logs -f deployment/a2a-registry-api
kubectl logs -f deployment/a2a-registry-worker
```

## Troubleshooting

View logs:
```bash
kubectl logs deployment/a2a-registry-api --tail=100
kubectl logs deployment/a2a-registry-worker --tail=100
```

Exec into pod:
```bash
kubectl exec -it deployment/a2a-registry-api -- /bin/bash
```

Check database connection:
```bash
kubectl run -it --rm debug --image=postgres:14 --restart=Never -- \
  psql $DATABASE_URL -c "SELECT COUNT(*) FROM agents;"
```
