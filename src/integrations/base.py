"""
Base classes for backend integrations.
"""
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod


class LogBackend(ABC):
    """Base class for log integrations"""
    
    @abstractmethod
    async def fetch_logs(
        self,
        since_minutes: int = 15,
        service: Optional[str] = None,
        level: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent logs.
        
        Returns:
            List of log entries with format:
            [
                {
                    "timestamp": "2025-12-29T10:30:00Z",
                    "level": "error",
                    "message": "Authentication failed",
                    "service": "api"
                }
            ]
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if backend is accessible"""
        pass


class MetricBackend(ABC):
    """Base class for metric integrations"""
    
    @abstractmethod
    async def fetch_metrics(self) -> Dict[str, Any]:
        """
        Fetch current system metrics.
        
        Returns:
            {
                "cpu_usage": 0.72,
                "memory_usage": 0.65,
                "error_rate": 0.03,
                "request_rate": 1250.5
            }
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if backend is accessible"""
        pass


class TraceBackend(ABC):
    """Base class for trace integrations"""
    
    @abstractmethod
    async def fetch_traces(
        self,
        since_minutes: int = 15,
        service: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent traces.
        
        Returns:
            List of trace spans
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if backend is accessible"""
        pass
