# RootOps Architecture

## Overview

RootOps is built as a microservices-oriented application with clear separation of concerns:

```
┌──────────────────────────────────────────────────────┐
│                   Client Layer                        │
│  (HTTP Clients, Dashboards, CI/CD Integrations)      │
└───────────────────────┬──────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────┐
│                  FastAPI Application                  │
│                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   API       │  │ Monitoring  │  │  Database   │ │
│  │  Routes     │  │ Middleware  │  │  Sessions   │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
└───────────────────────┬──────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────┐
│                  Service Layer                        │
│                                                       │
│  ┌──────────────┐ ┌───────────┐ ┌──────────────┐   │
│  │   Commit     │ │    Log    │ │    Trace     │   │
│  │  Analyzer    │ │  Analyzer │ │   Analyzer   │   │
│  └──────────────┘ └───────────┘ └──────────────┘   │
│                                                       │
│  ┌──────────────────────────────────────────────┐   │
│  │           Optimizer Service                   │   │
│  └──────────────────────────────────────────────┘   │
└───────────────────────┬──────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────┐
│                   ML Model Layer                      │
│                                                       │
│  ┌──────────────┐ ┌───────────┐ ┌──────────────┐   │
│  │  Breaking    │ │  Anomaly  │ │ Performance  │   │
│  │   Change     │ │ Detector  │ │  Predictor   │   │
│  │  Detector    │ │           │ │              │   │
│  └──────────────┘ └───────────┘ └──────────────┘   │
└───────────────────────┬──────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────┐
│                  Data Layer                           │
│                                                       │
│  ┌──────────────────────┐  ┌──────────────────────┐ │
│  │   PostgreSQL DB      │  │  Optional: Redis     │ │
│  │  (Analysis History)  │  │     (Caching)        │ │
│  └──────────────────────┘  └──────────────────────┘ │
└───────────────────────────────────────────────────────┘
```

## Components

### 1. API Layer (`src/api/`)

**Responsibility:** Handle HTTP requests and responses

- **routes.py** - RESTful API endpoints
- Request validation using Pydantic models
- Response serialization
- Error handling

### 2. Service Layer (`src/services/`)

**Responsibility:** Business logic and analysis

- **CommitAnalyzer** - Git commit analysis
- **LogAnalyzer** - Log aggregation and anomaly detection
- **TraceAnalyzer** - Distributed trace analysis
- **Optimizer** - Recommendation generation

Each service is independent and can be tested in isolation.

### 3. Model Layer (`src/models/`)

**Responsibility:** Machine learning and data models

- **predictions.py** - ML models (RandomForest, XGBoost, IsolationForest)
- **db_models.py** - SQLAlchemy database models
- **requests.py** - Pydantic request/response schemas

### 4. Infrastructure Layer

**Responsibility:** Cross-cutting concerns

- **config.py** - Configuration management
- **database.py** - Database connection pooling
- **monitoring.py** - Prometheus metrics

## Data Flow

### Commit Analysis Flow

```
1. Client sends POST /api/v1/analyze/commit
   ↓
2. API validates request (Pydantic)
   ↓
3. CommitAnalyzer extracts features
   ↓
4. BreakingChangeDetector predicts risk
   ↓
5. Optional: LLM enrichment (Claude API)
   ↓
6. Result stored in PostgreSQL
   ↓
7. Response returned to client
```

### Log Analysis Flow

```
1. Client sends POST /api/v1/analyze/logs
   ↓
2. API validates log entries
   ↓
3. LogAnalyzer aggregates metrics
   ↓
4. AnomalyDetector identifies patterns
   ↓
5. Anomalies classified by severity
   ↓
6. Result stored and returned
```

## Design Principles

### 1. **Separation of Concerns**
Each layer has a specific responsibility and doesn't cross boundaries.

### 2. **Dependency Injection**
Services are injected via FastAPI's dependency system for testability.

### 3. **Async by Default**
All I/O operations use `async/await` for better performance.

### 4. **Type Safety**
Pydantic models ensure type safety across API boundaries.

### 5. **Observability First**
Prometheus metrics at every layer for debugging and monitoring.

## Database Schema

```sql
-- Commit Analysis Results
CREATE TABLE commit_analyses (
    id SERIAL PRIMARY KEY,
    repository VARCHAR NOT NULL,
    commit_hash VARCHAR NOT NULL,
    changed_files INTEGER,
    lines_added INTEGER,
    lines_deleted INTEGER,
    risky_patterns JSONB,
    complexity_delta FLOAT,
    breaking_change_score FLOAT,
    semantic_risk_score FLOAT,
    semantic_summary TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Log Analysis Results
CREATE TABLE log_analyses (
    id SERIAL PRIMARY KEY,
    log_count INTEGER,
    error_count INTEGER,
    warning_count INTEGER,
    anomalies JSONB,
    spike_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Trace Analysis Results
CREATE TABLE trace_analyses (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR,
    trace_count INTEGER,
    slow_traces JSONB,
    bottlenecks JSONB,
    p95_latency FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Optimization Recommendations
CREATE TABLE optimizations (
    id SERIAL PRIMARY KEY,
    type VARCHAR,
    severity VARCHAR,
    title VARCHAR,
    description TEXT,
    impact VARCHAR,
    auto_fixable BOOLEAN,
    applied BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Scaling Considerations

### Horizontal Scaling

RootOps is stateless and can be scaled horizontally:

```yaml
# Kubernetes example
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rootops
spec:
  replicas: 3  # Scale to 3 instances
```

### Database Scaling

- Use PostgreSQL read replicas for query-heavy workloads
- Implement connection pooling (already configured)
- Archive old analysis results to cold storage

### Caching

- Redis can be added for frequently accessed data
- ML model predictions can be cached

## Security

### Authentication

Configure via environment variables:

```bash
# Future: JWT authentication
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
```

### Data Protection

- All database connections use SSL in production
- Sensitive data (API keys) stored in environment variables
- No logging of sensitive information

## Performance

### Benchmarks

On a 2-core, 4GB RAM instance:

- **Commit Analysis**: ~50ms average
- **Log Analysis** (100 logs): ~80ms average
- **Trace Analysis** (1000 traces): ~150ms average

### Optimization Tips

1. Use database indexes on frequently queried fields
2. Implement request caching for repeated queries
3. Batch multiple analyses in single request
4. Use async clients for external API calls

## Monitoring

### Key Metrics

- `rootops_http_requests_total` - Request count
- `rootops_predictions_total` - ML predictions
- `rootops_http_request_duration_seconds` - Latency

### Alerts

Recommended Prometheus alerts:

```yaml
- alert: HighErrorRate
  expr: rate(rootops_http_requests_total{status=~"5.."}[5m]) > 0.05
  
- alert: SlowResponses
  expr: histogram_quantile(0.95, rootops_http_request_duration_seconds) > 1
```

## Future Enhancements

- [ ] Real-time streaming analysis
- [ ] Custom ML model training
- [ ] Multi-tenancy support
- [ ] GraphQL API
- [ ] Webhook notifications
