"""
Optimization service

Generates optimization recommendations based on analysis results.
"""
from typing import List, Dict, Any
import logging
from src.models.requests import OptimizationRecommendation
from src.monitoring import recommendations_total

logger = logging.getLogger(__name__)


class Optimizer:
    """Generate optimization recommendations"""
    
    def __init__(self):
        self.initialized = True
        logger.info("Optimizer initialized")
    
    async def generate_recommendations(
        self,
        analysis_results: Dict[str, Any]
    ) -> List[OptimizationRecommendation]:
        """
        Generate optimization recommendations based on analysis
        
        Args:
            analysis_results: Combined analysis results from various analyzers
            
        Returns:
            List of optimization recommendations
        """
        recommendations = []
        
        # Check commit analysis
        commit_data = analysis_results.get("commit_analysis", {})
        if commit_data.get("risky_patterns"):
            for pattern in commit_data["risky_patterns"]:
                rec = OptimizationRecommendation(
                    type="code_quality",
                    severity="high",
                    title=f"Risky pattern detected: {pattern}",
                    description=f"The commit contains {pattern} which may cause issues",
                    impact="Reduce deployment risk by 30%",
                    auto_fixable=False
                )
                recommendations.append(rec)
                recommendations_total.labels(severity="high").inc()
        
        # Check log analysis
        log_data = analysis_results.get("log_analysis", {})
        if log_data.get("error_rate", 0) > 0.3:
            rec = OptimizationRecommendation(
                type="reliability",
                severity="critical",
                title="High error rate detected",
                description=f"Error rate is {log_data['error_rate']*100:.1f}%",
                impact="Improve service reliability",
                auto_fixable=True,
                implementation="Implement circuit breaker pattern"
            )
            recommendations.append(rec)
            recommendations_total.labels(severity="critical").inc()
        
        # Check trace analysis
        trace_data = analysis_results.get("trace_analysis", {})
        if trace_data.get("bottlenecks"):
            for bottleneck in trace_data["bottlenecks"][:3]:
                rec = OptimizationRecommendation(
                    type="performance",
                    severity="medium",
                    title=f"Performance bottleneck in {bottleneck['operation']}",
                    description=f"Average latency: {bottleneck['avg_duration_ms']}ms",
                    impact="Reduce latency by 40%",
                    auto_fixable=True,
                    implementation="Add caching layer or optimize database queries"
                )
                recommendations.append(rec)
                recommendations_total.labels(severity="medium").inc()
        
        return recommendations
