"""
Trace analysis service

Analyzes distributed traces for performance bottlenecks.
"""
from typing import Dict, Any, List
from datetime import datetime, timezone
import logging
import numpy as np
from src.monitoring import trace_analyses_total

logger = logging.getLogger(__name__)


class TraceAnalyzer:
    """Analyze distributed traces for performance issues"""
    
    def __init__(self):
        self.initialized = True
        logger.info("TraceAnalyzer initialized")
    
    async def analyze_traces(
        self,
        traces: List[Dict[str, Any]],
        service_name: str = None
    ) -> Dict[str, Any]:
        """
        Analyze trace data for bottlenecks
        
        Args:
            traces: List of trace spans
            service_name: Optional filter by service
            
        Returns:
            Dict with analysis results
        """
        if not traces:
            return {
                "trace_count": 0,
                "slow_traces": [],
                "bottlenecks": [],
                "p95_latency": 0.0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Filter by service if specified
        if service_name:
            traces = [t for t in traces if t.get("service") == service_name]
        
        # Extract durations
        durations = [t.get("duration_ms", 0) for t in traces]
        
        # Calculate percentiles
        p95_latency = float(np.percentile(durations, 95)) if durations else 0.0
        p50_latency = float(np.percentile(durations, 50)) if durations else 0.0
        
        # Find slow traces (> p95)
        slow_traces = [
            {
                "trace_id": t.get("trace_id"),
                "service": t.get("service"),
                "duration_ms": t.get("duration_ms"),
                "operation": t.get("operation")
            }
            for t in traces
            if t.get("duration_ms", 0) > p95_latency
        ]
        
        # Detect bottlenecks (operations with consistently high latency)
        operation_durations = {}
        for t in traces:
            op = t.get("operation", "unknown")
            duration = t.get("duration_ms", 0)
            if op not in operation_durations:
                operation_durations[op] = []
            operation_durations[op].append(duration)
        
        bottlenecks = []
        for op, durations_list in operation_durations.items():
            avg_duration = np.mean(durations_list)
            if avg_duration > p95_latency * 0.8:  # Consistently slow
                bottlenecks.append({
                    "operation": op,
                    "avg_duration_ms": round(avg_duration, 2),
                    "count": len(durations_list)
                })
        
        # Track metric
        trace_analyses_total.labels(
            result="bottleneck_detected" if bottlenecks else "success"
        ).inc()
        
        return {
            "trace_count": len(traces),
            "slow_traces": slow_traces[:10],  # Top 10
            "bottlenecks": sorted(bottlenecks, key=lambda x: x["avg_duration_ms"], reverse=True)[:5],
            "p95_latency": round(p95_latency, 2),
            "p50_latency": round(p50_latency, 2),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
