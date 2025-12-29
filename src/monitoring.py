"""
Prometheus metrics and monitoring

Provides application metrics for observability and monitoring.
"""
from fastapi import FastAPI
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import time

# HTTP Metrics
request_count = Counter(
    'rootops_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'rootops_http_request_duration_seconds',
    'HTTP request latency',
    ['endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Business Metrics
predictions_total = Counter(
    'rootops_predictions_total',
    'Total ML predictions made',
    ['model_type', 'result']
)

log_analyses_total = Counter(
    'rootops_log_analyses_total',
    'Total log analyses performed',
    ['result']
)

trace_analyses_total = Counter(
    'rootops_trace_analyses_total',
    'Total trace analyses performed',
    ['result']
)

recommendations_total = Counter(
    'rootops_recommendations_total',
    'Total optimization recommendations',
    ['severity']
)

active_models = Gauge(
    'rootops_active_models',
    'Number of loaded ML models'
)

healing_actions_total = Counter(
    'rootops_healing_actions_total',
    'Total self-healing actions',
    ['action_type', 'status']
)

db_operations_total = Counter(
    'rootops_db_operations_total',
    'Database operations',
    ['operation', 'status']
)


def setup_monitoring(app: FastAPI):
    """Configure monitoring middleware and metrics endpoint"""
    
    @app.middleware("http")
    async def monitor_requests(request, call_next):
        """Track HTTP request metrics"""
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Record metrics
        request_count.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        request_duration.labels(
            endpoint=request.url.path
        ).observe(duration)
        
        return response
    
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint"""
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
