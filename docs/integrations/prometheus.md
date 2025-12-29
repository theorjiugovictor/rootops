# Prometheus Integration

RootOps can analyze Prometheus metrics to detect anomalies and predict performance issues.

## Setup

### 1. Configure Prometheus to Scrape RootOps

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'rootops'
    static_configs:
      - targets: ['rootops:8000']
    metrics_path: '/metrics'
```

### 2. Query Prometheus from Your Code

```python
import requests
from datetime import datetime, timedelta

# Query Prometheus for metrics
prom_url = "http://prometheus:9090/api/v1/query_range"
query = "rate(http_requests_total[5m])"
end = datetime.now()
start = end - timedelta(hours=1)

response = requests.get(prom_url, params={
    'query': query,
    'start': start.timestamp(),
    'end': end.timestamp(),
    'step': '15s'
})

metrics_data = response.json()['data']['result']
```

### 3. Send to RootOps for Analysis

```python
# Convert Prometheus data to RootOps format
traces = []
for result in metrics_data:
    metric = result['metric']
    values = result['values']
    
    for timestamp, value in values:
        traces.append({
            'trace_id': f"{metric['job']}_{timestamp}",
            'service': metric.get('job', 'unknown'),
            'operation': metric.get('__name__', 'unknown'),
            'duration_ms': float(value) * 1000,
            'timestamp': datetime.fromtimestamp(timestamp).isoformat()
        })

# Analyze with RootOps
rootops_response = requests.post(
    'http://localhost:8000/api/v1/analyze/traces',
    json={'traces': traces}
)

print(rootops_response.json())
```

## Available RootOps Metrics

RootOps exposes these metrics at `/metrics`:

- `rootops_http_requests_total` - Total HTTP requests
- `rootops_http_request_duration_seconds` - Request latency histogram
- `rootops_predictions_total` - ML predictions made
- `rootops_log_analyses_total` - Log analyses performed
- `rootops_trace_analyses_total` - Trace analyses performed

## Alerting

Configure Prometheus alerts based on RootOps metrics:

```yaml
groups:
  - name: rootops_alerts
    rules:
      - alert: HighRootOpsErrorRate
        expr: rate(rootops_http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "RootOps has high error rate"
```
