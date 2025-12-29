"""
Prometheus metrics backend integration.
"""
import logging
from typing import Dict, Any
import httpx

from ..base import MetricBackend

logger = logging.getLogger(__name__)


class PrometheusBackend(MetricBackend):
    """Prometheus metrics backend"""
    
    def __init__(self, url: str):
        self.url = url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def fetch_metrics(self) -> Dict[str, Any]:
        """Fetch current metrics from Prometheus"""
        
        metrics = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "error_rate": 0.0,
            "request_rate": 0.0,
            "p95_latency": 0.0
        }
        
        # Query common metrics
        queries = {
            "cpu_usage": 'avg(rate(process_cpu_seconds_total[5m]))',
            "memory_usage": 'avg(process_resident_memory_bytes) / avg(node_memory_MemTotal_bytes)',
            "error_rate": 'sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))',
            "request_rate": 'sum(rate(http_requests_total[5m]))',
            "p95_latency": 'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))'
        }
        
        for metric_name, query in queries.items():
            try:
                response = await self.client.get(
                    f"{self.url}/api/v1/query",
                    params={"query": query}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    result = data.get("data", {}).get("result", [])
                    
                    if result:
                        value = float(result[0].get("value", [0, 0])[1])
                        metrics[metric_name] = value
            
            except Exception as e:
                logger.debug(f"Failed to fetch {metric_name}: {e}")
                continue
        
        logger.info(f"Fetched metrics from Prometheus: {metrics}")
        return metrics
    
    async def health_check(self) -> bool:
        """Check Prometheus availability"""
        try:
            response = await self.client.get(f"{self.url}/-/healthy")
            return response.status_code == 200
        except:
            return False
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
