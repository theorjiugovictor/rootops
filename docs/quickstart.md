# Quick Start Guide

## Installation

### Prerequisites

- Docker and Docker Compose
- 2GB RAM minimum
- Port 8000 available

### 1. Using Docker Compose (Recommended)

```bash
# Download docker-compose.yml
curl -O https://raw.githubusercontent.com/yourusername/rootops/main/docker-compose.yml

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

### 2. Using Docker Run

```bash
docker run -d \
  --name rootops \
  -p 8000:8000 \
  -e ALLOW_DB_INIT_FAILURE=true \
  rootops/rootops
```

### 3. Verify Installation

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","timestamp":"...","components":{"database":"connected",...}}
```

## First API Call

### Analyze a Commit

```bash
curl -X POST http://localhost:8000/api/v1/analyze/commit \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "my-app",
    "commit_hash": "abc123def456"
  }'
```

### Analyze Logs

```python
import requests

response = requests.post('http://localhost:8000/api/v1/analyze/logs', json={
    "logs": [
        {"level": "error", "message": "Database connection failed", "service": "api"},
        {"level": "info", "message": "Request processed", "service": "api"}
    ]
})

print(response.json())
```

## Interactive API Documentation

Visit http://localhost:8000/docs for Swagger UI with interactive API testing.

## Next Steps

- [API Reference](api-reference.md) - Complete API documentation
- [Integration Guides](integrations/) - Connect with Prometheus, Loki, Tempo
- [Configuration](../README.md#configuration) - Customize RootOps behavior
- [Examples](../examples/) - See real-world usage examples
