# Kubernetes Deployment

Deploy RootOps to Kubernetes with auto-scaling and high availability.

## Quick Start

```bash
kubectl apply -f deployment.yaml
```

## What Gets Deployed

- **Namespace**: `rootops`
- **PostgreSQL**: Single replica with persistent storage
- **RootOps**: 3 replicas with auto-scaling (2-10 pods)
- **Services**: LoadBalancer for external access
- **HPA**: Auto-scaling based on CPU/memory

## Access the Service

```bash
# Get external IP
kubectl get svc rootops -n rootops

# Access API docs
open http://<EXTERNAL-IP>:8000/docs
```

## Configuration

### Update Database Credentials

```bash
kubectl create secret generic rootops-postgres \
  --from-literal=postgres-user=rootops \
  --from-literal=postgres-password=your-secure-password \
  --from-literal=postgres-database=rootops \
  -n rootops
```

### Enable LLM Enrichment

```bash
kubectl create secret generic rootops-secrets \
  --from-literal=claude-api-key=your-api-key \
  -n rootops

# Update deployment to use secret
kubectl set env deployment/rootops \
  ENABLE_LLM_ENRICHMENT=true \
  CLAUDE_API_KEY=<secret> \
  -n rootops
```

## Monitoring

### View Logs

```bash
kubectl logs -f deployment/rootops -n rootops
```

### Check Metrics

```bash
kubectl top pods -n rootops
```

### Port Forward for Local Testing

```bash
kubectl port-forward svc/rootops 8000:8000 -n rootops
curl http://localhost:8000/health
```

## Production Recommendations

### 1. Use Helm Chart (Coming Soon)

```bash
helm install rootops rootops/rootops \
  --namespace rootops \
  --create-namespace \
  --values values.yaml
```

### 2. Configure Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: rootops-ingress
  namespace: rootops
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  rules:
  - host: rootops.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: rootops
            port:
              number: 8000
  tls:
  - hosts:
    - rootops.yourdomain.com
    secretName: rootops-tls
```

### 3. Set Resource Limits

Adjust based on your workload:

```yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "4000m"
```

### 4. Use PostgreSQL Operator

For production, consider using a PostgreSQL operator:

```bash
# CloudNativePG example
kubectl apply -f https://get.enterprisedb.io/cnpg/postgresql-operator-1.20.0.yaml
```

## Scaling

### Manual Scaling

```bash
kubectl scale deployment rootops --replicas=5 -n rootops
```

### Auto-scaling Configuration

HPA is already configured. Adjust thresholds:

```yaml
metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        averageUtilization: 70  # Scale at 70% CPU
```

## Troubleshooting

### Pods Not Starting

```bash
kubectl describe pod <pod-name> -n rootops
kubectl logs <pod-name> -n rootops
```

### Database Connection Issues

```bash
# Test connectivity
kubectl run -it --rm debug --image=postgres:15-alpine --restart=Never -n rootops -- \
  psql -h postgres -U rootops -d rootops
```

### Performance Issues

```bash
# Check resource usage
kubectl top pods -n rootops

# View metrics endpoint
kubectl port-forward svc/rootops 8000:8000 -n rootops
curl http://localhost:8000/metrics
```
