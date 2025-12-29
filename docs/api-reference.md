# API Reference

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Currently, RootOps does not require authentication for local deployments. For production use, configure authentication via environment variables.

---

## Endpoints

### 1. Analyze Commit

**POST** `/analyze/commit`

Analyze a git commit for breaking changes and code quality issues.

#### Request Body

```json
{
  "repository": "string",      // Required: Repository name
  "commit_hash": "string",     // Required: Commit hash or reference
  "diff": "string"             // Optional: Commit diff for LLM enrichment
}
```

#### Response

```json
{
  "repository": "myapp",
  "commit_hash": "abc123",
  "changed_files": 5,
  "lines_added": 120,
  "lines_deleted": 30,
  "risky_patterns": ["db_migration", "auth_logic"],
  "complexity_delta": 0.25,
  "semantic_risk_score": 0.75,        // If LLM enabled
  "semantic_summary": "High risk...",  // If LLM enabled
  "timestamp": "2025-12-28T10:00:00Z"
}
```

---

### 2. Analyze Logs

**POST** `/analyze/logs`

Analyze log entries for anomalies and error patterns.

#### Request Body

```json
{
  "logs": [
    {
      "level": "error",
      "message": "Connection timeout",
      "service": "api",
      "timestamp": "2025-12-28T10:00:00Z"
    }
  ],
  "time_range": {              // Optional
    "start": "2025-12-28T09:00:00Z",
    "end": "2025-12-28T11:00:00Z"
  }
}
```

#### Response

```json
{
  "log_count": 100,
  "error_count": 25,
  "warning_count": 10,
  "error_rate": 0.25,
  "anomalies": [
    {
      "type": "high_error_rate",
      "severity": "critical",
      "message": "Error rate is 25.0% (threshold: 30%)",
      "details": {
        "error_count": 25,
        "total_count": 100
      }
    }
  ],
  "spike_score": 0.7,
  "timestamp": "2025-12-28T10:00:00Z"
}
```

---

### 3. Analyze Traces

**POST** `/analyze/traces`

Analyze distributed traces for performance bottlenecks.

#### Request Body

```json
{
  "traces": [
    {
      "trace_id": "abc123",
      "service": "api",
      "operation": "GET /users",
      "duration_ms": 1500,
      "timestamp": "2025-12-28T10:00:00Z"
    }
  ],
  "service_name": "api"  // Optional filter
}
```

#### Response

```json
{
  "trace_count": 100,
  "slow_traces": [
    {
      "trace_id": "abc123",
      "service": "api",
      "operation": "GET /users",
      "duration_ms": 2500
    }
  ],
  "bottlenecks": [
    {
      "operation": "database_query",
      "avg_duration_ms": 1800,
      "count": 25
    }
  ],
  "p95_latency": 2000,
  "p50_latency": 800,
  "timestamp": "2025-12-28T10:00:00Z"
}
```

---

### 4. Get Optimization Recommendations

**POST** `/optimize`

Generate optimization recommendations based on analysis results.

#### Request Body

```json
{
  "commit_analysis": { /* commit analysis result */ },
  "log_analysis": { /* log analysis result */ },
  "trace_analysis": { /* trace analysis result */ }
}
```

#### Response

```json
[
  {
    "type": "performance",
    "severity": "high",
    "title": "Performance bottleneck in database_query",
    "description": "Average latency: 1800ms",
    "impact": "Reduce latency by 40%",
    "auto_fixable": true,
    "implementation": "Add caching layer or optimize queries"
  }
]
```

---

## System Endpoints

### Health Check

**GET** `/health`

```json
{
  "status": "healthy",
  "timestamp": "2025-12-28T10:00:00Z",
  "components": {
    "database": "connected",
    "ml_models": "loaded",
    "services": "ready"
  }
}
```

### Metrics

**GET** `/metrics`

Returns Prometheus metrics in text format.

---

## Error Responses

All endpoints return standard HTTP error codes:

- **400** - Bad Request (invalid input)
- **500** - Internal Server Error
- **503** - Service Unavailable

Error response format:

```json
{
  "detail": "Error message here"
}
```

---

## Rate Limiting

Currently no rate limiting is enforced. For production deployments, consider implementing rate limiting at the load balancer or API gateway level.

---

## Interactive Documentation

Visit http://localhost:8000/docs for Swagger UI with live API testing.
