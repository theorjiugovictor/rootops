"""
Machine Learning models for predictions

- Breaking Change Detection
- Anomaly Detection  
- Performance Prediction
"""
import logging
import random
from typing import Dict, Any
import numpy as np

logger = logging.getLogger(__name__)


class BreakingChangeDetector:
    """Detect breaking changes in commits using ML"""
    
    def __init__(self):
        self.model = None
        self.initialized = False
        logger.info("BreakingChangeDetector initialized")
    
    def predict(self, features: Dict[str, Any]) -> float:
        """
        Predict probability of breaking change
        
        Args:
            features: Dict with keys like changed_files, lines_added, risky_patterns, etc.
            
        Returns:
            Probability score (0-1)
        """
        # Enhanced scoring with GitHub enrichment data
        score = 0.0
        
        # Use risk_score if available from GitHub enrichment
        if "risk_score" in features and features["risk_score"] is not None:
            # GitHub enrichment provides 0-10 risk score
            score = features["risk_score"] / 10
            
            # Adjust based on author experience
            author_commits = features.get("author_commits_90d", 0)
            if author_commits > 0:
                # More experienced authors = lower risk
                experience_factor = min(author_commits / 100, 0.3)
                score *= (1 - experience_factor)
            
            # Adjust for commit type
            commit_type = features.get("commit_type", "other")
            if commit_type == "bugfix":
                score *= 0.8  # Bug fixes less risky than features
            elif commit_type == "feature":
                score *= 1.2  # Features more risky
            
            return min(1.0, score)
        
        # Fallback to heuristic if no GitHub data
        # More files changed = higher risk
        changed_files = features.get("changed_files", 0)
        score += min(0.3, changed_files * 0.02)
        
        # Large code additions = higher risk
        lines_added = features.get("lines_added", 0)
        score += min(0.2, lines_added * 0.0004)
        
        # Risky patterns = significant risk
        risky_patterns = features.get("risky_patterns", [])
        score += min(0.5, len(risky_patterns) * 0.15)
        
        return min(1.0, score)


class AnomalyDetector:
    """Detect anomalies in logs and metrics using ML"""
    
    def __init__(self):
        self.model = None
        self.initialized = False
        logger.info("AnomalyDetector initialized")
    
    def detect(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect anomalies in log data
        
        Args:
            data: Log analysis results
            
        Returns:
            Dict with anomaly detection results
        """
        anomalies = []
        score = 0.0
        
        error_rate = data.get("error_rate", 0.0)
        if error_rate > 0.3:
            anomalies.append({
                "type": "high_error_rate",
                "severity": "critical",
                "value": error_rate
            })
            score += 0.5
        
        spike_score = data.get("spike_score", 0.0)
        if spike_score > 0.6:
            anomalies.append({
                "type": "traffic_spike",
                "severity": "high",
                "value": spike_score
            })
            score += 0.3
        
        return {
            "is_anomaly": len(anomalies) > 0,
            "anomaly_score": min(1.0, score),
            "anomalies": anomalies
        }


class PerformancePredictor:
    """Predict performance degradation using ML"""
    
    def __init__(self):
        self.model = None
        self.initialized = False
        logger.info("PerformancePredictor initialized")
    
    def predict(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict performance degradation
        
        Args:
            metrics: Performance metrics (latency, throughput, etc.)
            
        Returns:
            Dict with prediction results
        """
        # Simple heuristic prediction
        p95_latency = metrics.get("p95_latency", 0.0)
        
        degradation_score = 0.0
        if p95_latency > 1000:  # > 1 second
            degradation_score = min(1.0, p95_latency / 3000)
        
        return {
            "will_degrade": degradation_score > 0.5,
            "degradation_score": degradation_score,
            "estimated_impact": "high" if degradation_score > 0.7 else "medium" if degradation_score > 0.4 else "low"
        }
