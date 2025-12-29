# Tempo Integration

Integrate RootOps with Grafana Tempo for distributed trace analysis.

## Setup

### 1. Configure Tempo URL

```bash
TEMPO_URL=http://tempo:3200
```

### 2. Send Traces to Tempo

Use OpenTelemetry to instrument your application:

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Configure OTLP exporter
otlp_exporter = OTLPSpanExporter(
    endpoint="http://tempo:4317",
    insecure=True
)

# Set up tracing
provider = TracerProvider()
processor = BatchSpanProcessor(otlp_exporter)
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)

# Create spans
with tracer.start_as_current_span("my-operation"):
    # Your code here
    pass
```

### 3. Query Traces from Tempo

```python
import requests
from datetime import datetime, timedelta

tempo_url = "http://tempo:3200/api/search"
end = datetime.now()
start = end - timedelta(hours=1)

# Search for traces
response = requests.get(tempo_url, params={
    'start': int(start.timestamp()),
    'end': int(end.timestamp()),
    'limit': 100,
    'service': 'my-app'
})

trace_ids = [t['traceID'] for t in response.json()['traces']]
```

### 4. Get Trace Details

```python
traces = []

for trace_id in trace_ids:
    # Get trace details
    trace_response = requests.get(
        f"http://tempo:3200/api/traces/{trace_id}"
    )
    
    trace_data = trace_response.json()
    
    # Extract spans
    for batch in trace_data.get('batches', []):
        for span in batch.get('spans', []):
            traces.append({
                'trace_id': trace_id,
                'service': batch.get('resource', {}).get('attributes', [{}])[0].get('value', {}).get('stringValue', 'unknown'),
                'operation': span.get('name', 'unknown'),
                'duration_ms': (span.get('endTimeUnixNano', 0) - span.get('startTimeUnixNano', 0)) / 1e6,
                'timestamp': datetime.fromtimestamp(span.get('startTimeUnixNano', 0) / 1e9).isoformat()
            })
```

### 5. Analyze with RootOps

```python
# Send to RootOps
response = requests.post(
    'http://localhost:8000/api/v1/analyze/traces',
    json={'traces': traces}
)

analysis = response.json()

print(f"Traces analyzed: {analysis['trace_count']}")
print(f"P95 latency: {analysis['p95_latency']}ms")
print(f"Slow traces: {len(analysis['slow_traces'])}")

for bottleneck in analysis['bottlenecks']:
    print(f"Bottleneck: {bottleneck['operation']} - {bottleneck['avg_duration_ms']}ms")
```

## Automated Performance Monitoring

```python
#!/usr/bin/env python3
"""
Continuous trace analysis for performance monitoring
"""

import requests
import time
from datetime import datetime, timedelta

def analyze_recent_traces():
    # Get traces from last 10 minutes
    end = datetime.now()
    start = end - timedelta(minutes=10)
    
    # Search Tempo
    search_response = requests.get('http://tempo:3200/api/search', params={
        'start': int(start.timestamp()),
        'end': int(end.timestamp()),
        'limit': 500
    })
    
    trace_ids = [t['traceID'] for t in search_response.json().get('traces', [])]
    
    # Collect trace details
    traces = []
    for trace_id in trace_ids[:100]:  # Limit to 100 for performance
        # Fetch and parse trace (implementation above)
        traces.extend(fetch_trace_spans(trace_id))
    
    # Analyze with RootOps
    if traces:
        response = requests.post(
            'http://localhost:8000/api/v1/analyze/traces',
            json={'traces': traces}
        )
        
        analysis = response.json()
        
        # Alert on high p95 latency
        if analysis['p95_latency'] > 1000:  # > 1 second
            alert_slow_performance(analysis)
        
        # Alert on bottlenecks
        for bottleneck in analysis['bottlenecks']:
            if bottleneck['avg_duration_ms'] > 500:
                alert_bottleneck(bottleneck)

if __name__ == '__main__':
    while True:
        analyze_recent_traces()
        time.sleep(600)  # 10 minutes
```

## OpenTelemetry Configuration

Full Python example with Flask:

```python
from flask import Flask
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource

app = Flask(__name__)

# Configure resource
resource = Resource.create({"service.name": "my-app"})

# Set up tracing
provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(
    OTLPSpanExporter(endpoint="http://tempo:4317", insecure=True)
)
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# Auto-instrument Flask
FlaskInstrumentor().instrument_app(app)

@app.route('/hello')
def hello():
    return 'Hello World!'
```
