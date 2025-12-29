# RootOps - Zero-Configuration Deployment Intelligence

## What We Built

A complete AI-powered DevOps intelligence platform that works immediately after deployment. No configuration files. No CI/CD integration needed. No manual API calls.

## Key Features

### 1. Auto-Polling Background Workers
- Polls GitHub every 5 minutes for new commits
- Automatically analyzes each commit for risk
- Monitors logs every 2 minutes for anomalies
- Checks metrics every minute (if Prometheus available)
- Learns continuously from all data

### 2. Multi-Backend Architecture
- **Loki**: Primary log backend with LogQL queries
- **File Logs**: Automatic fallback if Loki unavailable
- **Prometheus**: Metrics and system health
- **GitHub**: Commit enrichment and risk scoring
- **Auto-Detection**: Tests backends on startup, uses what's available

### 3. Intelligence Engine
- Continuous learning from incidents
- Pattern recognition across deployments
- Long-term memory (PostgreSQL)
- Correlation across commits, logs, and metrics
- Never forgets your software's lifecycle

### 4. Web Dashboard
- Real-time insights visualization
- Risk scores for recent commits
- Active deployment monitoring
- High-risk alerts
- Auto-refreshes every 30 seconds

### 5. Graceful Degradation
- **GitHub Only**: Commit analysis, risk scoring
- **GitHub + Logs**: Error correlation, anomaly detection
- **Full Stack**: System metrics, performance prediction, comprehensive analysis

## Usage Overview

See [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) for detailed integration patterns and deployment scenarios.

## Technical Architecture

```
┌─────────────────────────────────────────────────┐
│                  Auto-Poller                    │
│  ┌──────────────┐  ┌──────────────┐            │
│  │ GitHub Poll  │  │  Log Monitor │            │
│  │  (5 min)     │  │   (2 min)    │            │
│  └──────────────┘  └──────────────┘            │
└────────────┬────────────────┬───────────────────┘
             │                │
             ▼                ▼
┌─────────────────────────────────────────────────┐
│          Intelligence Engine                    │
│  ┌──────────────────────────────────────────┐  │
│  │  Commit Analysis → Risk Scoring          │  │
│  │  Log Correlation → Error Detection       │  │
│  │  Pattern Learning → Incident Prevention  │  │
│  │  Memory Storage → Continuous Learning    │  │
│  └──────────────────────────────────────────┘  │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│              PostgreSQL Memory                  │
│  ┌──────────────────────────────────────────┐  │
│  │  CommitMemory, DeploymentEvent           │  │
│  │  IncidentMemory, PatternMemory           │  │
│  │  CorrelationLearning                     │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│            Web Dashboard                        │
│  Auto-refresh every 30s                         │
│  Real-time insights                             │
│  Risk alerts                                    │
└─────────────────────────────────────────────────┘
```

## Backend Integration

### Logs (Priority Order)

1. **Grafana Loki** (preferred)
   - LogQL queries
   - Service filtering
   - Error level detection
   
2. **File Logs** (fallback)
   - Reads `/logs/*.log`
   - Glob pattern matching
   - Regex level extraction

### Metrics

1. **Prometheus**
   - PromQL queries
   - CPU, memory, errors, latency
   - Anomaly detection

### Commits

1. **GitHub API**
   - Rich commit details
   - Files changed
   - Author history
   - Risk scoring

## What Makes This Special

### 1. Zero Configuration
No config files. No YAML. No integration steps. Just run.

### 2. Graceful Intelligence
Works with GitHub alone. Gets better with more data. Never requires everything.

### 3. Continuous Learning
Never forgets. Learns from every incident. Patterns emerge over time.

### 4. Auto-Detection
Tests backends on startup. Uses what's available. Logs what it found.

### 5. No Manual Work
Auto-polling eliminates manual API calls. Dashboard auto-refreshes. Just watch.

## Files Created

### Core Services
- `src/services/auto_poller.py` - Background workers for continuous monitoring
- `src/services/intelligence_engine.py` - The brain that learns and correlates
- `src/services/github_enrichment.py` - GitHub API integration

### Backend Integration
- `src/integrations/base.py` - Abstract backend interfaces
- `src/integrations/detector.py` - Auto-detection logic
- `src/integrations/logs/loki.py` - Loki backend
- `src/integrations/logs/file.py` - File log fallback
- `src/integrations/metrics/prometheus.py` - Prometheus backend

### Dashboard
- `src/static/dashboard.html` - Web UI
- `src/api/dashboard_routes.py` - Dashboard API

### Database Models
- `src/models/db_models.py` - Memory tables (commits, deployments, incidents, patterns)

### Configuration
- `src/config.py` - Settings with auto-polling options
- `.env.example` - Environment template

### Documentation
- `docs/INTEGRATION_GUIDE.md` - How to use with existing apps
- `README.md` - Updated with zero-config deployment

## User Experience Flow

### First 5 Minutes
1. User runs Docker image
2. Sets GITHUB_TOKEN and GITHUB_REPO
3. Opens dashboard at localhost:8000/dashboard
4. Sees "Loading commits..."
5. After 5 minutes, sees analyzed commits

### First Hour
1. Auto-poller fetched 10 commits
2. Each commit analyzed and scored
3. Dashboard shows risk levels
4. User sees high-risk commits highlighted
5. Logs (if available) being monitored

### First Day
1. 100+ commits analyzed
2. Patterns starting to emerge
3. User records first incident
4. Intelligence Engine correlates incident with commit
5. Learning begins

### First Week
1. 500+ commits in memory
2. Multiple incidents recorded
3. Patterns identified (e.g., "database migrations → incidents")
4. Auto-polling working flawlessly
5. User trusts the insights

### First Month
1. Thousands of commits analyzed
2. Reliable pattern recognition
3. Accurate incident prediction
4. User's team relies on dashboard
5. RootOps is now part of workflow

## Deployment Patterns

### 1. Standalone (Simplest)
```bash
docker run -p 8000:8000 -e GITHUB_TOKEN=xxx -e GITHUB_REPO=xxx rootops/rootops
```

### 2. Docker Compose (Better)
```yaml
services:
  rootops:
    image: rootops/rootops
    environment:
      - GITHUB_TOKEN
      - GITHUB_REPO
      - LOKI_URL
```

### 3. Kubernetes (Production)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rootops
spec:
  template:
    spec:
      containers:
      - name: rootops
        image: rootops/rootops
        env:
        - name: GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: github
              key: token
```

## API Endpoints

### Intelligence Engine
- `POST /api/v1/intelligence/deployment` - Analyze deployment
- `POST /api/v1/intelligence/incident` - Record incident
- `POST /api/v1/intelligence/monitor` - Monitor deployment

### Dashboard
- `GET /api/dashboard/overview` - Dashboard data
- `GET /api/dashboard/commits/{sha}` - Commit details
- `GET /api/dashboard/deployments` - Recent deployments

### Static
- `GET /dashboard` - Web dashboard UI

## Configuration Options

### Required
```bash
GITHUB_TOKEN=ghp_xxx
GITHUB_REPO=owner/repo
```

### Optional (Auto-Detected)
```bash
LOKI_URL=http://loki:3100
PROMETHEUS_URL=http://prometheus:9090
```

### Auto-Polling
```bash
ENABLE_AUTO_POLLING=true
POLL_GITHUB_INTERVAL_SECONDS=300
POLL_LOGS_INTERVAL_SECONDS=120
AUTO_ANALYZE_NEW_COMMITS=true
```

### Learning
```bash
ENABLE_CONTINUOUS_LEARNING=true
MEMORY_RETENTION_DAYS=365
PATTERN_CONFIDENCE_THRESHOLD=0.7
```

## What Users Get

### Without Any Work
- Commit risk scores
- Pattern learning
- Incident correlation
- Web dashboard
- Auto-refresh insights

### With Log Integration
- Error detection
- Log anomalies
- Deployment monitoring
- Root cause hints

### With Metrics Integration
- System health awareness
- Performance degradation prediction
- Comprehensive analysis

### With Incident Recording
- Faster pattern learning
- Better predictions
- Personalized insights

## Summary

RootOps is now a complete zero-configuration deployment intelligence platform that:

1. **Works immediately** - Pull Docker image, set 2 env vars, done
2. **Learns continuously** - Auto-polls GitHub, logs, metrics
3. **Adapts gracefully** - Uses what's available, works without everything
4. **Requires no maintenance** - Background workers handle everything
5. **Provides real-time insights** - Dashboard auto-refreshes
6. **Gets smarter over time** - Long-term memory, pattern learning

**The user literally just runs it and watches the dashboard. That's the entire experience.**
