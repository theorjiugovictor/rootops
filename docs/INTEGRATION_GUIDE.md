# How to Use RootOps with Your Existing Application

This guide shows how to integrate RootOps into your existing production environment.

## TL;DR - Fastest Path

```bash
# 1. Set environment variables
export GITHUB_TOKEN=ghp_your_token_here
export GITHUB_REPO=yourorg/yourrepo

# 2. Run RootOps
docker run -d \
  -p 8000:8000 \
  -e GITHUB_TOKEN=$GITHUB_TOKEN \
  -e GITHUB_REPO=$GITHUB_REPO \
  rootops/rootops

# 3. Open dashboard
open http://localhost:8000/dashboard

# Done. RootOps is now auto-polling and learning.
```

## Integration Patterns

### Pattern 1: Zero-Config (Recommended)

**Best for**: Teams who want insights immediately without changing existing infrastructure.

**How it works**:
- RootOps auto-polls GitHub every 5 minutes
- Automatically analyzes new commits
- Monitors logs (if Loki available, otherwise falls back to files)
- Displays insights on web dashboard

**Setup**:
```bash
docker run -d \
  -p 8000:8000 \
  -e GITHUB_TOKEN=your_token \
  -e GITHUB_REPO=owner/repo \
  -e LOKI_URL=http://your-loki:3100 \
  -e PROMETHEUS_URL=http://your-prometheus:9090 \
  rootops/rootops
```

**What you get**:
- Real-time commit risk scores
- Automatic deployment monitoring
- Pattern learning from incidents
- Zero maintenance required

### Pattern 2: CI/CD Integration

**Best for**: Teams with existing CI/CD pipelines who want deployment-time analysis.

**GitHub Actions Example**:
```yaml
name: Deploy with RootOps

on:
  push:
    branches: [main]

jobs:
  analyze-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Analyze with RootOps
        run: |
          curl -X POST http://rootops:8000/api/v1/intelligence/deployment \
            -H "Content-Type: application/json" \
            -d '{
              "commit_sha": "${{ github.sha }}",
              "repository": "${{ github.repository }}",
              "deployment_id": "${{ github.run_id }}"
            }' | jq .
          
      - name: Deploy
        run: ./deploy.sh
```

**GitLab CI Example**:
```yaml
stages:
  - analyze
  - deploy

analyze:
  stage: analyze
  script:
    - |
      curl -X POST http://rootops:8000/api/v1/intelligence/deployment \
        -H "Content-Type: application/json" \
        -d "{
          \"commit_sha\": \"$CI_COMMIT_SHA\",
          \"repository\": \"$CI_PROJECT_PATH\",
          \"deployment_id\": \"$CI_PIPELINE_ID\"
        }"

deploy:
  stage: deploy
  script:
    - ./deploy.sh
```

### Pattern 3: Kubernetes Sidecar

**Best for**: Kubernetes environments wanting in-cluster analysis.

**Deployment**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      containers:
      - name: myapp
        image: myapp:latest
        ports:
        - containerPort: 8080
        
      - name: rootops
        image: rootops/rootops:latest
        env:
        - name: GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: github-secret
              key: token
        - name: GITHUB_REPO
          value: "yourorg/yourrepo"
        - name: LOKI_URL
          value: "http://loki:3100"
        - name: PROMETHEUS_URL
          value: "http://prometheus:9090"
        ports:
        - containerPort: 8000
```

**Service**:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: rootops
spec:
  selector:
    app: myapp
  ports:
  - port: 8000
    targetPort: 8000
```

### Pattern 4: Post-Deployment Webhook

**Best for**: Teams using deployment tools like Spinnaker, ArgoCD, Flux.

**After Deployment**:
```bash
# Call RootOps to start monitoring
curl -X POST http://rootops:8000/api/v1/intelligence/monitor \
  -H "Content-Type: application/json" \
  -d '{
    "deployment_id": "prod-deploy-12345",
    "commit_sha": "abc123",
    "repository": "owner/repo",
    "environment": "production"
  }'
```

**What happens**:
1. RootOps fetches commit details from GitHub
2. Analyzes risk based on files changed
3. Monitors logs for the next hour
4. Correlates errors with the deployment
5. Alerts if incident detected
6. Learns from the outcome

### Pattern 5: Manual Incident Recording

**Best for**: Learning from production incidents.

**When incident occurs**:
```bash
curl -X POST http://rootops:8000/api/v1/intelligence/incident \
  -H "Content-Type: application/json" \
  -d '{
    "deployment_id": "prod-deploy-12345",
    "commit_sha": "abc123",
    "repository": "owner/repo",
    "incident_type": "service_degradation",
    "severity": "high",
    "description": "Memory leak caused pod restarts",
    "resolution": "Reverted commit and added memory limits"
  }'
```

**What happens**:
1. RootOps stores the incident
2. Correlates it with the commit
3. Learns patterns (e.g., "memory allocation changes → incidents")
4. Applies learning to future commits
5. Warns about similar changes

## Backend Configuration

RootOps auto-detects backends. Just set environment variables:

```bash
# Minimal (GitHub only)
GITHUB_TOKEN=your_token
GITHUB_REPO=owner/repo

# Optional observability backends
LOKI_URL=http://loki:3100         # For log analysis
PROMETHEUS_URL=http://prometheus:9090  # For metrics
```

Backends are automatically tested on startup and gracefully degrade if unavailable.

## Configuration Options

### Environment Variables

```bash
# Required
GITHUB_TOKEN=ghp_xxxxx          # GitHub personal access token
GITHUB_REPO=owner/repo          # Repository to monitor

# Optional - Observability
LOKI_URL=http://loki:3100
PROMETHEUS_URL=http://prometheus:9090
TEMPO_URL=http://tempo:3200

# Optional - Auto-Polling
ENABLE_AUTO_POLLING=true
POLL_GITHUB_INTERVAL_SECONDS=300    # Default: 5 minutes
POLL_LOGS_INTERVAL_SECONDS=120      # Default: 2 minutes
AUTO_ANALYZE_NEW_COMMITS=true

# Optional - Learning
ENABLE_CONTINUOUS_LEARNING=true
MEMORY_RETENTION_DAYS=365
PATTERN_CONFIDENCE_THRESHOLD=0.7

# Optional - Database
DATABASE_URL=postgresql://user:pass@postgres:5432/rootops
ALLOW_DB_INIT_FAILURE=false     # Set true for testing without DB
```

### Docker Compose (Full Stack)

```yaml
version: '3.8'

services:
  rootops:
    image: rootops/rootops:latest
    ports:
      - "8000:8000"
    environment:
      GITHUB_TOKEN: ${GITHUB_TOKEN}
      GITHUB_REPO: ${GITHUB_REPO}
      LOKI_URL: http://loki:3100
      PROMETHEUS_URL: http://prometheus:9090
      DATABASE_URL: postgresql://rootops:rootops@postgres:5432/rootops
    depends_on:
      - postgres
      - loki
      - prometheus
    volumes:
      - ./logs:/logs:ro  # Optional: file-based logs
  
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: rootops
      POSTGRES_PASSWORD: rootops
      POSTGRES_DB: rootops
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    command: -config.file=/etc/loki/local-config.yaml
  
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

volumes:
  postgres_data:
```

## Using the Dashboard

After starting RootOps, open http://localhost:8000/dashboard

**Dashboard shows**:
- **Active Deployments**: Number of deployments currently being monitored
- **Incident Probability**: Average risk across recent commits
- **Total Insights**: Number of commits analyzed
- **Recent Commits**: Last 20 commits with risk scores
- **Alerts**: High-risk commits that need attention

**Auto-refresh**: Dashboard refreshes every 30 seconds

## API Endpoints

See [API Reference](./api-reference.md) for full documentation.

**Key endpoints:**
- `POST /api/v1/intelligence/deployment` - Analyze deployment risk
- `POST /api/v1/intelligence/incident` - Record incident for learning
- `POST /api/v1/intelligence/monitor` - Monitor deployment health
- `GET /api/dashboard/overview` - Dashboard data
- `GET /dashboard` - Web dashboard UI

## Deployment Strategies

### 1. Proof of Concept
- Run RootOps locally with Docker
- Point to production GitHub repo
- Monitor read-only for 1 week
- Review insights on dashboard

### 2. Non-Production Integration
- Deploy to staging environment
- Integrate with staging CI/CD
- Test auto-polling and alerts
- Validate incident learning

### 3. Production Rollout
- Deploy as Kubernetes sidecar
- Connect to production Loki/Prometheus
- Enable auto-polling
- Start recording incidents
- Let Intelligence Engine learn

## Best Practices

1. **Start Simple**: Begin with GitHub-only mode, add logs later
2. **Record Incidents**: Manually record past incidents for faster learning
3. **Review Dashboard Daily**: Check high-risk commits before deployment
4. **Trust the Learning**: After 10+ incidents, patterns become reliable
5. **Use Auto-Polling**: Zero-config mode requires no maintenance
6. **Monitor First Hour**: Critical period after deployment
7. **Document Resolutions**: Helps Intelligence Engine learn better

## Troubleshooting

### RootOps not analyzing commits
```bash
# Check auto-poller status
curl http://localhost:8000/health

# Check logs
docker logs rootops
```

### No data in dashboard
- Wait 5 minutes for first poll cycle
- Verify GITHUB_TOKEN and GITHUB_REPO are set
- Check GitHub API rate limits

### Can't connect to Loki/Prometheus
- RootOps will fall back to file logs automatically
- Check LOKI_URL and PROMETHEUS_URL are correct
- Verify network connectivity

### Database connection failed
- Set `ALLOW_DB_INIT_FAILURE=true` for testing
- For production, verify PostgreSQL is running
- Check DATABASE_URL format

## Migration from Manual Monitoring

**Before** (manual):
```bash
# Deploy
./deploy.sh

# Wait for alerts
# Check Grafana manually
# Investigate logs manually
# Hope you find the issue
```

**After** (RootOps):
```bash
# Deploy
./deploy.sh

# RootOps automatically:
# - Analyzed the commit before deployment
# - Warned about high-risk patterns
# - Monitors logs for next hour
# - Alerts if incident detected
# - Learns from the outcome
```

## Next Steps

1. Start with [Quick Start](../README.md#quick-start)
2. Review [Architecture Documentation](../docs/architecture.md)
3. Explore [API Reference](../docs/api-reference.md)
4. Check [GitHub Integration Guide](../docs/integrations/github.md)

## Support

- GitHub Issues: https://github.com/yourorg/rootops/issues
- Documentation: https://github.com/yourorg/rootops/tree/main/docs
- Examples: https://github.com/yourorg/rootops/tree/main/examples
