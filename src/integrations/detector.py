"""
Auto-detect available backends.
"""
import logging
import os
from typing import Dict, Optional

from src.config import settings
from .logs.loki import LokiBackend
from .logs.file import FileBackend
from .metrics.prometheus import PrometheusBackend
from .base import LogBackend, MetricBackend

logger = logging.getLogger(__name__)


class BackendDetector:
    """Detect and initialize available backends"""
    
    def __init__(self):
        self.log_backend: Optional[LogBackend] = None
        self.metric_backend: Optional[MetricBackend] = None
    
    async def detect(self) -> Dict[str, str]:
        """
        Auto-detect available backends.
        
        Returns:
            {
                "logs": "loki" | "file" | "none",
                "metrics": "prometheus" | "none"
            }
        """
        detected = {
            "logs": "none",
            "metrics": "none"
        }
        
        # Detect log backend
        if settings.LOKI_URL:
            loki = LokiBackend(settings.LOKI_URL)
            if await loki.health_check():
                self.log_backend = loki
                detected["logs"] = "loki"
                logger.info(f"Log backend: Loki ({settings.LOKI_URL})")
            else:
                await loki.close()
        
        # Fallback to file-based logs
        # 2. File Backend (for PM2, fallback)
        if not self.log_backend and os.path.exists(settings.LOG_PATH):
            file_backend = FileBackend(settings.LOG_PATH)
            if await file_backend.health_check():
                self.log_backend = file_backend
                detected["logs"] = "file"
                logger.info(f"Log backend: File ({settings.LOG_PATH})")
        
        # Detect metric backend
        if settings.PROMETHEUS_URL:
            prometheus = PrometheusBackend(settings.PROMETHEUS_URL)
            if await prometheus.health_check():
                self.metric_backend = prometheus
                detected["metrics"] = "prometheus"
                logger.info(f"Metric backend: Prometheus ({settings.PROMETHEUS_URL})")
            else:
                await prometheus.close()
        
        if detected["logs"] == "none":
            logger.warning("No log backend detected - log analysis disabled")
        
        if detected["metrics"] == "none":
            logger.warning("No metric backend detected - metric analysis disabled")
        
        return detected
    
    async def get_logs(self, since_minutes: int = 15):
        """Fetch logs from detected backend"""
        if self.log_backend:
            return await self.log_backend.fetch_logs(since_minutes)
        return []
    
    async def get_metrics(self):
        """Fetch metrics from detected backend"""
        if self.metric_backend:
            return await self.metric_backend.fetch_metrics()
        return {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "error_rate": 0.0,
            "request_rate": 0.0
        }
