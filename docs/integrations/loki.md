# Loki Integration

Integrate RootOps with Grafana Loki for log analysis and anomaly detection.

## Setup

### 1. Configure Loki URL

Set the environment variable:

```bash
LOKI_URL=http://loki:3100
```

### 2. Query Logs from Loki

```python
import requests
from datetime import datetime, timedelta

loki_url = "http://loki:3100/loki/api/v1/query_range"
query = '{job="my-app"}'
end = datetime.now()
start = end - timedelta(hours=1)

response = requests.get(loki_url, params={
    'query': query,
    'start': int(start.timestamp() * 1e9),  # nanoseconds
    'end': int(end.timestamp() * 1e9),
    'limit': 1000
})

loki_logs = response.json()['data']['result']
```

### 3. Convert to RootOps Format

```python
# Parse Loki logs
logs = []
for stream in loki_logs:
    labels = stream['stream']
    service = labels.get('job', 'unknown')
    
    for entry in stream['values']:
        timestamp_ns, log_line = entry
        
        # Parse log level from log line (adjust to your format)
        level = 'info'
        if 'ERROR' in log_line.upper():
            level = 'error'
        elif 'WARN' in log_line.upper():
            level = 'warning'
        
        logs.append({
            'level': level,
            'message': log_line,
            'service': service,
            'timestamp': datetime.fromtimestamp(int(timestamp_ns) / 1e9).isoformat()
        })
```

### 4. Analyze with RootOps

```python
# Send to RootOps for analysis
response = requests.post(
    'http://localhost:8000/api/v1/analyze/logs',
    json={'logs': logs}
)

analysis = response.json()
print(f"Error rate: {analysis['error_rate']}")
print(f"Anomalies detected: {len(analysis['anomalies'])}")

for anomaly in analysis['anomalies']:
    print(f"- {anomaly['type']}: {anomaly['message']}")
```

## Automated Log Analysis Pipeline

```python
#!/usr/bin/env python3
"""
Automated log analysis pipeline
Runs every 5 minutes to analyze recent logs
"""

import requests
import time
from datetime import datetime, timedelta

def analyze_recent_logs():
    # Query last 5 minutes of logs
    end = datetime.now()
    start = end - timedelta(minutes=5)
    
    loki_response = requests.get('http://loki:3100/loki/api/v1/query_range', params={
        'query': '{job=~".+"}',  # All jobs
        'start': int(start.timestamp() * 1e9),
        'end': int(end.timestamp() * 1e9),
        'limit': 5000
    })
    
    # Convert and analyze
    logs = parse_loki_response(loki_response.json())
    
    rootops_response = requests.post(
        'http://localhost:8000/api/v1/analyze/logs',
        json={'logs': logs}
    )
    
    analysis = rootops_response.json()
    
    # Alert on critical anomalies
    for anomaly in analysis['anomalies']:
        if anomaly['severity'] == 'critical':
            send_alert(anomaly)

if __name__ == '__main__':
    while True:
        analyze_recent_logs()
        time.sleep(300)  # 5 minutes
```

## LogQL Query Examples

```python
# Error logs only
query = '{job="my-app"} |= "error"'

# Specific service
query = '{service="api", env="production"}'

# JSON parsing
query = '{job="my-app"} | json | level="error"'

# Rate query
query = 'rate({job="my-app"}[5m])'
```
