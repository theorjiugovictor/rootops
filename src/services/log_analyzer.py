"""
Log analysis service

Analyzes log entries for anomalies and patterns.
"""
from typing import Dict, Any, List
from datetime import datetime, timezone
from collections import Counter
import logging
from src.monitoring import log_analyses_total

logger = logging.getLogger(__name__)


class LogAnalyzer:
    """Analyze logs for anomalies and error patterns"""
    
    def __init__(self):
        self.initialized = True
        logger.info("LogAnalyzer initialized")
    
    async def analyze_logs(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze log entries for anomalies
        
        Args:
            logs: List of log entries with level, message, service, etc.
            
        Returns:
            Dict with analysis results including anomalies
        """
        log_count = len(logs)
        if log_count == 0:
            return {
                "log_count": 0,
                "error_count": 0,
                "warning_count": 0,
                "anomalies": [],
                "spike_score": 0.0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Normalize log levels
        levels = [(l.get("level") or "").lower() for l in logs]
        error_count = sum(1 for lvl in levels if lvl in ("error", "critical"))
        warn_count = sum(1 for lvl in levels if lvl == "warning")
        
        error_rate = error_count / log_count
        
        # Detect anomalies
        anomalies = []
        
        # High error rate
        if error_rate > 0.3:
            anomalies.append({
                "type": "high_error_rate",
                "severity": "critical" if error_rate > 0.7 else "high",
                "message": f"Error rate is {error_rate*100:.1f}% (threshold: 30%)",
                "details": {
                    "error_count": error_count,
                    "total_count": log_count,
                    "error_rate": error_rate
                }
            })
        
        # Repeated errors
        error_messages = [
            l.get("message", "")
            for l in logs
            if (l.get("level") or "").lower() in ("error", "critical")
        ]
        
        if error_messages:
            message_counts = Counter(error_messages)
            for msg, count in message_counts.items():
                if count >= 3:
                    anomalies.append({
                        "type": "repeated_error",
                        "severity": "high",
                        "message": f"Error repeated {count} times",
                        "details": {
                            "error_message": msg[:100],
                            "occurrences": count
                        }
                    })
        
        # Calculate spike score
        spike_score = 0.0
        if anomalies:
            spike_score = min(0.9, 0.3 + (len(anomalies) * 0.2))
        
        # Track metric
        result_label = "anomaly_detected" if anomalies else "success"
        log_analyses_total.labels(result=result_label).inc()
        
        return {
            "log_count": log_count,
            "error_count": error_count,
            "warning_count": warn_count,
            "error_rate": round(error_rate, 3),
            "anomalies": anomalies,
            "spike_score": round(spike_score, 3),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
