"""
Loki log backend integration.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import httpx

from ..base import LogBackend

logger = logging.getLogger(__name__)


class LokiBackend(LogBackend):
    """Grafana Loki log backend"""
    
    def __init__(self, url: str):
        self.url = url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def fetch_logs(
        self,
        since_minutes: int = 15,
        service: Optional[str] = None,
        level: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch logs from Loki"""
        
        # Build LogQL query
        query = '{job=~".+"}'
        if service:
            query = f'{{service="{service}"}}'
        
        # Time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=since_minutes)
        
        params = {
            "query": query,
            "start": int(start_time.timestamp() * 1e9),  # nanoseconds
            "end": int(end_time.timestamp() * 1e9),
            "limit": 1000
        }
        
        try:
            response = await self.client.get(
                f"{self.url}/loki/api/v1/query_range",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            logs = []
            
            # Parse Loki response
            for stream in data.get("data", {}).get("result", []):
                labels = stream.get("stream", {})
                service_name = labels.get("service", labels.get("job", "unknown"))
                
                for values in stream.get("values", []):
                    timestamp_ns, log_line = values
                    
                    # Parse log level from line (basic heuristic)
                    log_level = "info"
                    log_line_lower = log_line.lower()
                    if "error" in log_line_lower or "fatal" in log_line_lower:
                        log_level = "error"
                    elif "warn" in log_line_lower:
                        log_level = "warning"
                    
                    # Filter by level if specified
                    if level and log_level != level:
                        continue
                    
                    logs.append({
                        "timestamp": datetime.fromtimestamp(
                            int(timestamp_ns) / 1e9
                        ).isoformat() + "Z",
                        "level": log_level,
                        "message": log_line,
                        "service": service_name
                    })
            
            logger.info(f"Fetched {len(logs)} logs from Loki")
            return logs
            
        except Exception as e:
            logger.error(f"Failed to fetch logs from Loki: {e}")
            return []
    
    async def health_check(self) -> bool:
        """Check Loki availability"""
        try:
            response = await self.client.get(f"{self.url}/ready")
            return response.status_code == 200
        except:
            return False
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
