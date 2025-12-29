# RootOps

<div align="center">

![RootOps Logo](https://via.placeholder.com/200x200.png?text=RootOps)

**AI-Powered DevOps Intelligence Platform**

[![Docker Pulls](https://img.shields.io/docker/pulls/rootops/rootops)](https://hub.docker.com/r/rootops/rootops)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Stars](https://img.shields.io/github/stars/yourusername/rootops)](https://github.com/yourusername/rootops)

*Predictive insights for your DevOps pipeline - not reactive responses*

[Quick Start](#quick-start) •
[Documentation](#documentation) •
[Examples](#examples) •
[Contributing](#contributing)

</div>

---

## What is RootOps?

RootOps is an **AI-powered DevOps intelligence platform** that analyzes your commits, logs, and traces to provide **predictive insights** before problems occur. Unlike traditional monitoring tools that react to issues, RootOps learns from your software's historical lifecycle to predict and prevent problems.

**The Intelligence Engine** - Think of it as an engineer that never forgets. It continuously learns from:
- Every commit and its outcome
- Every incident and its cause
- Patterns that emerge over time
- Your team's behavior and system evolution

The more you use RootOps, the smarter it gets.

### Key Features

- **Intelligent Deployment Analysis** - Comprehensive risk assessment with learned context
- **Breaking Change Prediction** - Analyze commits to detect breaking changes *before* deployment  
- **Anomaly Detection** - Identify unusual patterns in logs and metrics using ML
- **Performance Prediction** - Forecast performance degradation from historical trends
- **Continuous Learning** - Builds long-term memory, never forgets your software's lifecycle
- **Pattern Recognition** - Learns which changes lead to incidents over time
- **GitHub Enrichment** - Deep commit analysis with detailed statistics
- **LLM Enrichment** - Optional semantic analysis using Claude AI (metadata-only mode for security)
- **Optimization Recommendations** - AI-generated actionable insights
- **Auto-Polling** - Continuously monitors GitHub, logs, and metrics without manual intervention
- **Web Dashboard** - Real-time visualization of insights and alerts
- **Multi-Backend Support** - Works with Loki, Prometheus, file logs, or gracefully degrades

### How It Works

RootOps uses a **graceful intelligence scaling** model:
- Works with GitHub alone (commit analysis, risk scoring)
- Gets better with logs (error correlation, anomaly detection)
- Best with full observability (metrics, performance prediction)

Auto-detects available backends on startup. No configuration required.

## Requirements

- **Python**: 3.11 or 3.12 (3.13+ not yet supported by ML dependencies)
- **Docker**: For containerized deployment
- **PostgreSQL**: 15+ (optional for local dev with `ALLOW_DB_INIT_FAILURE=true`)
- **GitHub Token**: For commit enrichment (optional but recommended)

## Quick Start

### Option 1: Interactive Script (Easiest)

```bash
curl -fsSL https://raw.githubusercontent.com/yourorg/rootops/main/quickstart.sh | bash
```

Or download and run:
```bash
./quickstart.sh
```

The script will:
- Check Docker installation
- Ask for GitHub token and repository
- Optionally configure Loki/Prometheus
- Start RootOps
- Open dashboard automatically

### Option 2: Docker Run (Fast)

```bash
# Pull and run
docker run -p 8000:8000 \
  -e GITHUB_TOKEN=your_token \
  -e GITHUB_REPO=owner/repo \
  rootops/rootops

# Open dashboard
open http://localhost:8000/dashboard
```

### Option 3: Docker Compose (Full Stack)

```bash
# Run with all components
docker-compose up -d
open http://localhost:8000/docs
```

> **Note**: See [INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md) for advanced deployment patterns.

###Verify Installation

```bash
curl http://localhost:8000/health
```

##  Usage

### Intelligence Engine (Recommended)

The main endpoint that provides comprehensive analysis with learning:

```bash
curl -X POST http://localhost:8000/api/v1/intelligence/deployment \
  -H "Content-Type: application/json" \
  -d '{
    "commit_sha": "abc123",
    "repository": "myorg/myapp",
    "deployment_id": "deploy-prod-001"
  }'
```

**Response with Full Intelligence:**
```json
{
  "commit_sha": "abc123",
  "repository": "myorg/myapp",
  "analysis": {
    "risk_score": 7.8,
    "complexity": 6.5,
    "blast_radius": 4,
    "patterns_detected": ["auth_logic", "db_migration"]
  },
  "system_state": {
    "cpu_usage": 0.72,
    "error_rate": 0.03,
    "health_score": 0.85
  },
  "intelligence": {
    "similar_incidents": [
      {
        "severity": "P1",
        "root_cause_commit": "def456",
        "occurred_at": "2024-12-15T14:30:00Z",
        "patterns": ["auth_logic"]
      }
    ],
    "pattern_matches": [
      {
        "pattern_type": "auth_logic",
        "confidence": 0.89,
        "occurrence_count": 47,
        "typical_impact": "HIGH"
      }
    ],
    "author_history": {
      "total_commits": 23,
      "incident_rate": 0.13
    }
  },
  "prediction": {
    "incident_probability": 0.78,
    "confidence": 0.85,
    "expected_impact": "HIGH",
    "time_to_incident": "2.3 hours",
    "likely_failure_mode": "Authentication/Authorization failure"
  },
  "recommendations": [
    "⚠️ Use staged/canary rollout",
    "🔐 Enable verbose auth logging before deploy",
    "📚 3 similar incidents in past 90 days - review history"
  ],
  "action": "STAGED_ROLLOUT",
  "monitoring": {
    "watch_metrics": ["error_rate", "auth_failures"],
    "monitoring_duration": "12 hours"
  },
  "learned_from": "247 past events"
}
```

### Record Incidents (For Learning)

Help RootOps learn from incidents:

```bash
curl -X POST http://localhost:8000/api/v1/intelligence/incident \
  -H "Content-Type: application/json" \
  -d '{
    "incident_id": "INC-2024-001",
    "severity": "P1",
    "description": "Auth service outage",
    "root_cause_commit": "abc123",
    "patterns": ["auth_logic", "memory_leak"]
  }'
```

The Intelligence Engine updates its knowledge and improves future predictions.

### Post-Deployment Monitoring

Continuously monitor deployment health and detect issues:

```bash
# Call this every 5-10 minutes after deployment
curl -X POST http://localhost:8000/api/v1/intelligence/monitor \
  -H "Content-Type: application/json" \
  -d '{
    "deployment_id": "deploy-prod-001",
    "duration_minutes": 30,
    "current_logs": [
      {"level": "error", "message": "Authentication failed for user", "timestamp": "2024-12-28T10:30:00Z"},
      {"level": "error", "message": "Database connection timeout", "timestamp": "2024-12-28T10:31:00Z"}
    ]
  }'
```

**Response:**
```json
{
  "deployment_id": "deploy-prod-001",
  "commit_sha": "abc123",
  "monitoring_duration": "30 minutes",
  "baseline": {
    "error_rate": 0.02,
    "health_score": 0.95
  },
  "current": {
    "error_rate": 0.18,
    "error_count": 47,
    "anomalies": [
      {"type": "high_error_rate", "severity": "critical"}
    ]
  },
  "changes": {
    "error_rate_increase": 0.16,
    "degradation_percent": 800.0,
    "new_error_patterns": ["auth_failure", "database_connection"]
  },
  "health_status": "CRITICAL",
  "rollback": {
    "recommended": true,
    "urgency": "IMMEDIATE",
    "reason": "Critical errors detected - immediate rollback required",
    "action": "Execute rollback now"
  }
}
```

Integrate into your deployment pipeline:

```yaml
# CI/CD deployment script
deploy:
  script:
    - deploy_app
    - |
      # Monitor for 30 minutes
      for i in {1..6}; do
        sleep 300  # 5 minutes
        HEALTH=$(curl -X POST http://rootops:8000/api/v1/intelligence/monitor \
          -H "Content-Type: application/json" \
          -d "{\"deployment_id\": \"$DEPLOY_ID\", \"duration_minutes\": $((i*5)), \"current_logs\": $(fetch_logs)}")
        
        if [ "$(echo $HEALTH | jq -r '.rollback.recommended')" == "true" ]; then
          echo "RootOps recommends rollback!"
          rollback_deployment
          exit 1
        fi
      done
```

### Analyze a Commit (Legacy)

```bash
curl -X POST http://localhost:8000/api/v1/analyze/commit \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "myapp",
    "commit_hash": "abc123",
    "diff": "optional diff content"
  }'
```

**Response:**
```json
{
  "repository": "myapp",
  "commit_hash": "abc123",
  "changed_files": 5,
  "lines_added": 120,
  "lines_deleted": 30,
  "risky_patterns": ["db_migration", "auth_logic"],
  "complexity_delta": 0.25,
  "timestamp": "2025-12-28T10:00:00Z"
}
```

### Analyze Logs

```bash
curl -X POST http://localhost:8000/api/v1/analyze/logs \
  -H "Content-Type: application/json" \
  -d '{
    "logs": [
      {"level": "error", "message": "Connection timeout", "service": "api"},
      {"level": "error", "message": "Connection timeout", "service": "api"},
      {"level": "warning", "message": "High memory usage", "service": "worker"}
    ]
  }'
```

**Response:**
```json
{
  "log_count": 3,
  "error_count": 2,
  "warning_count": 1,
  "error_rate": 0.667,
  "anomalies": [
    {
      "type": "high_error_rate",
      "severity": "critical",
      "message": "Error rate is 66.7% (threshold: 30%)"
    },
    {
      "type": "repeated_error",
      "severity": "high",
      "message": "Error repeated 2 times"
    }
  ],
  "spike_score": 0.7
}
```

### Analyze Traces

```bash
curl -X POST http://localhost:8000/api/v1/analyze/traces \
  -H "Content-Type: application/json" \
  -d '{
    "traces": [
      {"trace_id": "t1", "service": "api", "operation": "GET /users", "duration_ms": 1500},
      {"trace_id": "t2", "service": "api", "operation": "POST /orders", "duration_ms": 2300}
    ]
  }'
```

## Configuration

RootOps is configured via environment variables or a `.env` file:

```bash
# GitHub Integration (for enriched commit analysis)
GITHUB_TOKEN=ghp_your_token
GITHUB_REPO=owner/repository

# Feature Flags
ENABLE_BREAKING_CHANGE_DETECTION=true
ENABLE_ANOMALY_DETECTION=true
ENABLE_PERFORMANCE_PREDICTION=true

# LLM Enrichment (Optional)
ENABLE_LLM_ENRICHMENT=true
CLAUDE_API_KEY=your-api-key

# Analysis Thresholds
BREAKING_CHANGE_THRESHOLD=0.7
ANOMALY_THRESHOLD=0.8

# Observability Integrations
LOKI_URL=http://loki:3100
PROMETHEUS_URL=http://prometheus:9090
TEMPO_URL=http://tempo:3200
```

See [`.env.example`](.env.example) for all options.

## Architecture

```
┌─────────────────────────────────────────┐
│         Your Applications               │
│   (Commits, Logs, Traces, Metrics)      │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│          RootOps API                    │
│      (FastAPI + ML Models)              │
└─────────────────┬───────────────────────┘
                  │
     ┌────────────┼────────────┐
     │            │            │
┌────▼───┐  ┌────▼───┐  ┌─────▼────┐
│Commit  │  │  Log   │  │  Trace   │
│Analyzer│  │Analyzer│  │ Analyzer │
└────┬───┘  └────┬───┘  └─────┬────┘
     │            │            │
     └────────────┼────────────┘
                  │
         ┌────────▼─────────┐
         │  ML Models       │
         │ • RandomForest   │
         │ • XGBoost        │
         │ • IsolationFor   │
         └──────────────────┘
```

## 📚 Documentation

- [Quick Start Guide](docs/quickstart.md)
- [API Reference](docs/api-reference.md)
- [Architecture Overview](docs/architecture.md)
- [Integration Guides](docs/integrations/)
  - [GitHub](docs/integrations/github.md) - Enriched commit analysis
  - [Prometheus](docs/integrations/prometheus.md)
  - [Loki](docs/integrations/loki.md)
  - [Tempo](docs/integrations/tempo.md)

## Examples

Check out the [`examples/`](examples/) directory for:

- **Docker Compose** - Full observability stack with Grafana, Prometheus, Loki
- **Kubernetes** - Helm charts for production deployment
- **CI/CD Integration** - GitHub Actions, GitLab CI examples
- **Python Client** - SDK for programmatic access

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/rootops.git
cd rootops

# Create virtual environment (requires Python 3.11 or 3.12)
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run locally (without database)
ALLOW_DB_INIT_FAILURE=true uvicorn src.main:app --reload

# Or with Docker Compose for full stack
docker-compose up -d
```

**Note**: If you're on Python 3.14+, use Docker instead as ML dependencies don't support it yet.

## Monitoring

RootOps exposes Prometheus metrics at `/metrics`:

```bash
curl http://localhost:8000/metrics
```

**Key Metrics:**
- `rootops_predictions_total` - Total ML predictions
- `rootops_http_requests_total` - HTTP request count
- `rootops_log_analyses_total` - Log analyses performed

## Security

- See [SECURITY.md](SECURITY.md) for reporting vulnerabilities
- All API endpoints support authentication (configure via environment)
- Database credentials should be stored securely (use secrets management)

## License

RootOps is open source software licensed under the [MIT License](LICENSE).

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=yourusername/rootops&type=Date)](https://star-history.com/#yourusername/rootops&Date)

## Community

- **GitHub Discussions** - Ask questions and share ideas
- **Discord** - Join our community server
- **Twitter** - Follow [@rootops](https://twitter.com/rootops) for updates

---

<div align="center">

**Built by the RootOps community**

[Website](https://rootops.io) • [Documentation](https://docs.rootops.io) • [Blog](https://blog.rootops.io)

</div>
