# Full Observability Stack Example

This example deploys RootOps with a complete observability stack including Grafana, Prometheus, Loki, and Tempo.

## Components

- **RootOps** - Intelligence Engine
- **PostgreSQL** - Database
- **Grafana** - Visualization
- **Prometheus** - Metrics collection
- **Loki** - Log aggregation
- **Tempo** - Distributed tracing
- **Promtail** - Log shipping to Loki

## Quick Start

```bash
docker-compose up -d
```

## Access URLs

- **RootOps API**: http://localhost:8000/docs
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Loki**: http://localhost:3100

## Architecture

```
Your Apps → Prometheus/Loki/Tempo → RootOps → Analysis/Predictions
                ↓
            Grafana (Visualization)
```

## Usage

1. Send metrics to Prometheus (port 9090)
2. Send logs to Loki (port 3100)
3. Send traces to Tempo (port 3200)
4. RootOps analyzes data via API
5. Visualize in Grafana

## Example: Analyze Prometheus Metrics

```python
import requests

# Query Prometheus
prom_response = requests.get('http://localhost:9090/api/v1/query', 
    params={'query': 'up'})

# Send to RootOps for analysis
rootops_response = requests.post('http://localhost:8000/api/v1/analyze/logs',
    json={'logs': [...]})
```
