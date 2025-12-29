"""
Intelligence Engine - The Brain of RootOps

Continuously learns from:
- Commits and their outcomes
- Incidents and their causes
- Patterns over time
- Team behavior
- System evolution

Like an engineer that never forgets.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
import json
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.github_enrichment import GitHubEnrichmentService
from src.services.log_analyzer import LogAnalyzer
from src.services.trace_analyzer import TraceAnalyzer
from src.models.db_models import (
    CommitMemory, 
    IncidentMemory, 
    PatternMemory,
    DeploymentEvent,
    CorrelationLearning
)

logger = logging.getLogger(__name__)


class IntelligenceEngine:
    """
    The brain that connects all signals and learns over time.
    
    Responsibilities:
    1. Correlate commits → deployments → incidents
    2. Learn from historical patterns
    3. Predict outcomes based on experience
    4. Generate contextual recommendations
    5. Never forget - accumulate knowledge forever
    """
    
    def __init__(
        self,
        db_session: AsyncSession,
        github_service: GitHubEnrichmentService,
        log_analyzer: LogAnalyzer,
        trace_analyzer: TraceAnalyzer
    ):
        self.db = db_session
        self.github = github_service
        self.log_analyzer = log_analyzer
        self.trace_analyzer = trace_analyzer
        self.learning_enabled = True
        logger.info("Intelligence Engine initialized - memory system active")
    
    async def analyze_deployment(
        self,
        commit_sha: str,
        repository: str,
        deployment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive deployment analysis with full context.
        
        This is the main intelligence function that:
        1. Analyzes the commit
        2. Recalls similar past situations
        3. Checks current system state
        4. Predicts outcome
        5. Provides actionable guidance
        """
        logger.info(f"Intelligence Engine analyzing deployment: {commit_sha[:8]}")
        
        # Step 1: Gather all signals in parallel
        commit_data, system_state, historical_context = await asyncio.gather(
            self._analyze_commit(commit_sha),
            self._get_system_state(),
            self._recall_similar_situations(commit_sha)
        )
        
        # Step 2: Build comprehensive context
        context = {
            "commit": commit_data,
            "system_state": system_state,
            "memory": historical_context,
            "timestamp": datetime.utcnow()
        }
        
        # Step 3: Predict outcome using learned patterns
        prediction = await self._predict_outcome(context)
        
        # Step 4: Generate intelligent recommendations
        recommendations = self._generate_recommendations(context, prediction)
        
        # Step 5: Record this deployment for future learning
        await self._record_deployment(commit_sha, repository, context, prediction, deployment_id)
        
        return {
            "commit_sha": commit_sha,
            "repository": repository,
            "analysis": {
                "risk_score": commit_data.get("risk_score", 0),
                "complexity": commit_data.get("complexity_score", 0),
                "blast_radius": commit_data.get("blast_radius", 0),
                "patterns_detected": commit_data.get("risky_patterns", [])
            },
            "system_state": system_state,
            "intelligence": {
                "similar_incidents": historical_context.get("similar_incidents", []),
                "pattern_matches": historical_context.get("pattern_matches", []),
                "author_history": historical_context.get("author_stats", {}),
                "time_correlation": historical_context.get("time_patterns", {})
            },
            "prediction": {
                "incident_probability": prediction["probability"],
                "confidence": prediction["confidence"],
                "expected_impact": prediction["expected_impact"],
                "time_to_incident": prediction.get("time_to_incident"),
                "likely_failure_mode": prediction.get("failure_mode")
            },
            "recommendations": recommendations,
            "action": self._decide_action(prediction),
            "monitoring": {
                "watch_metrics": self._what_to_monitor(commit_data),
                "alert_thresholds": self._get_alert_thresholds(prediction),
                "monitoring_duration": self._get_monitoring_window(commit_data)
            },
            "learned_from": f"{historical_context.get('total_memories', 0)} past events"
        }
    
    async def _analyze_commit(self, commit_sha: str) -> Dict:
        """Analyze commit with GitHub enrichment."""
        github_data = await self.github.get_commit_details(commit_sha)
        
        if github_data:
            return {
                "sha": github_data.sha,
                "author": github_data.author,
                "email": github_data.email,
                "files_changed": github_data.files_changed,
                "additions": github_data.additions,
                "deletions": github_data.deletions,
                "risk_score": github_data.risk_score,
                "complexity_score": github_data.complexity_score,
                "blast_radius": github_data.blast_radius,
                "test_ratio": github_data.test_ratio,
                "commit_type": github_data.commit_type,
                "risky_patterns": self.github.extract_risky_patterns(github_data.files),
                "timestamp": github_data.timestamp
            }
        
        return {"sha": commit_sha, "risk_score": 5.0}
    
    async def _get_system_state(self) -> Dict:
        """Get current system health metrics including logs and traces."""
        system_state = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "error_rate": 0.0,
            "p95_latency": 0.0,
            "active_alerts": 0,
            "health_score": 1.0,
            "log_anomalies": [],
            "recent_errors": 0
        }
        
        # Query recent logs (last 15 minutes)
        try:
            recent_logs = await self._fetch_recent_logs(minutes=15)
            if recent_logs:
                log_analysis = await self.log_analyzer.analyze_logs(recent_logs)
                system_state["error_rate"] = log_analysis.get("error_rate", 0.0)
                system_state["recent_errors"] = log_analysis.get("error_count", 0)
                system_state["log_anomalies"] = log_analysis.get("anomalies", [])
                
                # Adjust health score based on log health
                if log_analysis.get("spike_score", 0) > 0.5:
                    system_state["health_score"] -= 0.3
        except Exception as e:
            logger.warning(f"Failed to fetch recent logs: {e}")
        
        # TODO: Query Prometheus for CPU/memory metrics
        # TODO: Query Tempo for trace latency
        
        # Calculate overall health score
        system_state["health_score"] = max(0.0, min(1.0, system_state["health_score"]))
        
        return system_state
    
    async def _fetch_recent_logs(self, minutes: int = 15) -> List[Dict]:
        """
        Fetch recent logs from Loki or configured log source.
        """
        # TODO: Implement actual Loki query
        # For now, return empty to prevent failures
        # This will be populated when LOKI_URL is configured
        return []
    
    async def _recall_similar_situations(self, commit_sha: str) -> Dict:
        """
        Query memory database for similar past situations.
        This is where continuous learning happens.
        """
        # Find similar commits that led to incidents
        similar_incidents = await self._find_similar_incidents()
        
        # Find learned patterns
        pattern_matches = await self._find_matching_patterns()
        
        # Get author statistics
        author_stats = await self._get_author_statistics()
        
        # Temporal patterns (day of week, time of day)
        time_patterns = await self._get_temporal_patterns()
        
        return {
            "similar_incidents": similar_incidents,
            "pattern_matches": pattern_matches,
            "author_stats": author_stats,
            "time_patterns": time_patterns,
            "total_memories": await self._count_total_memories()
        }
    
    async def _find_similar_incidents(self) -> List[Dict]:
        """Find incidents with similar characteristics."""
        # Query last 90 days of incidents
        ninety_days_ago = datetime.utcnow() - timedelta(days=90)
        
        result = await self.db.execute(
            select(IncidentMemory)
            .where(IncidentMemory.occurred_at >= ninety_days_ago)
            .order_by(IncidentMemory.occurred_at.desc())
            .limit(10)
        )
        
        incidents = result.scalars().all()
        
        return [
            {
                "incident_id": incident.id,
                "severity": incident.severity,
                "root_cause_commit": incident.root_cause_commit,
                "occurred_at": incident.occurred_at.isoformat(),
                "time_to_detect": incident.time_to_detect_minutes,
                "patterns": incident.patterns
            }
            for incident in incidents
        ]
    
    async def _find_matching_patterns(self) -> List[Dict]:
        """Find learned patterns that match current situation."""
        result = await self.db.execute(
            select(PatternMemory)
            .where(PatternMemory.confidence >= 0.7)
            .order_by(PatternMemory.occurrence_count.desc())
            .limit(5)
        )
        
        patterns = result.scalars().all()
        
        return [
            {
                "pattern_type": pattern.pattern_type,
                "description": pattern.description,
                "occurrence_count": pattern.occurrence_count,
                "confidence": pattern.confidence,
                "typical_impact": pattern.typical_impact
            }
            for pattern in patterns
        ]
    
    async def _get_author_statistics(self) -> Dict:
        """Get author-specific statistics from memory."""
        # TODO: Query author's historical success/failure rate
        return {
            "total_commits": 0,
            "incident_rate": 0.0,
            "avg_risk_score": 0.0,
            "expertise_areas": []
        }
    
    async def _get_temporal_patterns(self) -> Dict:
        """Learn from time-based patterns (weekends, nights, etc)."""
        # TODO: Query temporal incident patterns
        now = datetime.utcnow()
        
        return {
            "day_of_week": now.strftime("%A"),
            "hour_of_day": now.hour,
            "is_weekend": now.weekday() >= 5,
            "is_off_hours": now.hour < 6 or now.hour > 22,
            "historical_risk_this_time": 0.0
        }
    
    async def _count_total_memories(self) -> int:
        """Count total events in memory."""
        result = await self.db.execute(
            select(func.count(CommitMemory.id))
        )
        return result.scalar() or 0
    
    async def _predict_outcome(self, context: Dict) -> Dict:
        """
        Predict deployment outcome based on learned patterns.
        
        This uses:
        1. Commit characteristics
        2. Historical similar situations
        3. Current system state
        4. Time-based patterns
        """
        commit = context["commit"]
        system = context["system_state"]
        memory = context["memory"]
        
        # Base probability from commit risk
        base_risk = commit.get("risk_score", 5.0) / 10
        
        # Adjust based on system state
        system_factor = 1.0 - system.get("health_score", 1.0)
        
        # Adjust based on historical patterns
        historical_factor = len(memory.get("similar_incidents", [])) * 0.1
        
        # Adjust based on author history
        author_factor = memory.get("author_stats", {}).get("incident_rate", 0.0)
        
        # Temporal adjustment
        time_factor = 0.2 if memory["time_patterns"].get("is_off_hours") else 0.0
        
        # Combined probability
        probability = min(
            base_risk + system_factor + historical_factor + author_factor + time_factor,
            1.0
        )
        
        # Confidence based on available data
        confidence = self._calculate_confidence(memory)
        
        return {
            "probability": probability,
            "confidence": confidence,
            "expected_impact": self._estimate_impact(commit, memory),
            "time_to_incident": self._estimate_time_to_incident(memory),
            "failure_mode": self._predict_failure_mode(commit, memory)
        }
    
    def _calculate_confidence(self, memory: Dict) -> float:
        """Calculate prediction confidence based on available memories."""
        total_memories = memory.get("total_memories", 0)
        
        if total_memories < 10:
            return 0.3  # Low confidence
        elif total_memories < 50:
            return 0.6  # Medium confidence
        elif total_memories < 200:
            return 0.8  # High confidence
        else:
            return 0.95  # Very high confidence
    
    def _estimate_impact(self, commit: Dict, memory: Dict) -> str:
        """Estimate incident impact if it occurs."""
        blast_radius = commit.get("blast_radius", 1)
        
        if blast_radius >= 5:
            return "CRITICAL"
        elif blast_radius >= 3:
            return "HIGH"
        elif blast_radius >= 2:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _estimate_time_to_incident(self, memory: Dict) -> Optional[str]:
        """Estimate when incident might occur after deployment."""
        similar_incidents = memory.get("similar_incidents", [])
        
        if similar_incidents:
            avg_time = sum(
                inc.get("time_to_detect", 0) 
                for inc in similar_incidents
            ) / len(similar_incidents)
            
            if avg_time < 60:
                return f"{int(avg_time)} minutes"
            else:
                return f"{avg_time / 60:.1f} hours"
        
        return "Unknown - no historical data"
    
    def _predict_failure_mode(self, commit: Dict, memory: Dict) -> Optional[str]:
        """Predict most likely failure mode."""
        patterns = commit.get("risky_patterns", [])
        
        if "auth_logic" in patterns:
            return "Authentication/Authorization failure"
        elif "db_migration" in patterns:
            return "Database schema issues"
        elif "api_contract" in patterns:
            return "API compatibility break"
        elif "dependency_version" in patterns:
            return "Dependency conflict"
        
        # Learn from historical incidents
        similar = memory.get("similar_incidents", [])
        if similar:
            return similar[0].get("patterns", ["Unknown"])[0]
        
        return None
    
    def _generate_recommendations(self, context: Dict, prediction: Dict) -> List[str]:
        """Generate actionable recommendations based on intelligence."""
        recommendations = []
        commit = context["commit"]
        memory = context["memory"]
        prob = prediction["probability"]
        
        # Risk-based recommendations
        if prob >= 0.8:
            recommendations.append("⛔ BLOCK DEPLOYMENT - High incident probability")
        elif prob >= 0.6:
            recommendations.append("⚠️  Use staged/canary rollout")
        elif prob >= 0.4:
            recommendations.append("📊 Deploy with enhanced monitoring")
        
        # Pattern-based recommendations
        if "auth_logic" in commit.get("risky_patterns", []):
            recommendations.append("🔐 Enable verbose auth logging before deploy")
        
        if "db_migration" in commit.get("risky_patterns", []):
            recommendations.append("💾 Test migration on staging with production data volume")
        
        # Test coverage
        if commit.get("test_ratio", 1.0) < 0.2:
            recommendations.append("🧪 Low test coverage - add integration tests")
        
        # Temporal recommendations
        if memory["time_patterns"].get("is_off_hours"):
            recommendations.append("🌙 Off-hours deploy - ensure on-call coverage")
        
        if memory["time_patterns"].get("is_weekend"):
            recommendations.append("📅 Weekend deploy - consider waiting for Monday")
        
        # System state
        if context["system_state"].get("error_rate", 0) > 0.05:
            recommendations.append("🚨 System already has elevated errors - stabilize first")
        
        # Historical learning
        similar_incidents = memory.get("similar_incidents", [])
        if similar_incidents:
            recommendations.append(
                f"📚 {len(similar_incidents)} similar incidents in past 90 days - review history"
            )
        
        return recommendations
    
    def _decide_action(self, prediction: Dict) -> str:
        """Decide recommended action based on prediction."""
        prob = prediction["probability"]
        
        if prob >= 0.8:
            return "BLOCK"
        elif prob >= 0.6:
            return "STAGED_ROLLOUT"
        elif prob >= 0.4:
            return "PROCEED_WITH_CAUTION"
        else:
            return "PROCEED"
    
    def _what_to_monitor(self, commit_data: Dict) -> List[str]:
        """Determine what metrics to monitor after deployment."""
        metrics = ["error_rate", "p95_latency", "cpu_usage"]
        
        patterns = commit_data.get("risky_patterns", [])
        
        if "auth_logic" in patterns:
            metrics.extend(["auth_failures", "unauthorized_attempts"])
        
        if "db_migration" in patterns:
            metrics.extend(["db_connection_pool", "query_time", "deadlocks"])
        
        if "api_contract" in patterns:
            metrics.extend(["4xx_errors", "5xx_errors", "request_validation_errors"])
        
        return metrics
    
    def _get_alert_thresholds(self, prediction: Dict) -> Dict:
        """Adjust alert thresholds based on risk."""
        prob = prediction["probability"]
        
        # Higher risk = stricter thresholds
        if prob >= 0.7:
            return {
                "error_rate": 0.01,  # 1%
                "p95_latency_increase": 0.10  # 10% increase
            }
        elif prob >= 0.4:
            return {
                "error_rate": 0.03,  # 3%
                "p95_latency_increase": 0.20  # 20% increase
            }
        else:
            return {
                "error_rate": 0.05,  # 5%
                "p95_latency_increase": 0.30  # 30% increase
            }
    
    def _get_monitoring_window(self, commit_data: Dict) -> str:
        """Determine how long to monitor post-deployment."""
        risk = commit_data.get("risk_score", 5.0)
        
        if risk >= 8.0:
            return "24 hours"
        elif risk >= 6.0:
            return "12 hours"
        elif risk >= 4.0:
            return "6 hours"
        else:
            return "2 hours"
    
    async def _record_deployment(
        self,
        commit_sha: str,
        repository: str,
        context: Dict,
        prediction: Dict,
        deployment_id: Optional[str]
    ):
        """
        Record deployment for continuous learning.
        This builds the engine's memory over time.
        """
        commit_data = context["commit"]
        
        # Record commit memory
        commit_memory = CommitMemory(
            sha=commit_sha,
            repository=repository,
            author=commit_data.get("author"),
            author_email=commit_data.get("email"),
            files_changed=commit_data.get("files_changed", 0),
            lines_added=commit_data.get("additions", 0),
            lines_deleted=commit_data.get("deletions", 0),
            risk_score=commit_data.get("risk_score", 0),
            complexity_score=commit_data.get("complexity_score", 0),
            blast_radius=commit_data.get("blast_radius", 0),
            test_ratio=commit_data.get("test_ratio", 0),
            commit_type=commit_data.get("commit_type"),
            risky_patterns=commit_data.get("risky_patterns", []),
            committed_at=commit_data.get("timestamp", datetime.utcnow())
        )
        
        self.db.add(commit_memory)
        
        # Record deployment event
        deployment = DeploymentEvent(
            deployment_id=deployment_id or f"deploy-{commit_sha[:8]}",
            commit_sha=commit_sha,
            repository=repository,
            deployed_at=datetime.utcnow(),
            predicted_risk=prediction["probability"],
            predicted_impact=prediction["expected_impact"],
            recommended_action=self._decide_action(prediction),
            system_state=context["system_state"]
        )
        
        self.db.add(deployment)
        
        await self.db.commit()
        
        logger.info(f"Recorded deployment memory for {commit_sha[:8]}")
    
    async def record_incident(
        self,
        incident_id: str,
        severity: str,
        description: str,
        root_cause_commit: Optional[str] = None,
        patterns: Optional[List[str]] = None
    ):
        """
        Record incident for learning.
        This is how the engine learns from failures.
        """
        # Find related deployment
        deployment = None
        if root_cause_commit:
            result = await self.db.execute(
                select(DeploymentEvent)
                .where(DeploymentEvent.commit_sha == root_cause_commit)
                .order_by(DeploymentEvent.deployed_at.desc())
                .limit(1)
            )
            deployment = result.scalar_one_or_none()
        
        time_to_detect = None
        if deployment:
            time_to_detect = int(
                (datetime.utcnow() - deployment.deployed_at).total_seconds() / 60
            )
        
        incident = IncidentMemory(
            incident_id=incident_id,
            severity=severity,
            description=description,
            root_cause_commit=root_cause_commit,
            occurred_at=datetime.utcnow(),
            time_to_detect_minutes=time_to_detect,
            patterns=patterns or []
        )
        
        self.db.add(incident)
        
        # Update deployment with incident outcome
        if deployment:
            deployment.resulted_in_incident = True
            deployment.incident_id = incident_id
        
        await self.db.commit()
        
        # Learn new patterns
        await self._learn_from_incident(incident, deployment)
        
        logger.info(f"Recorded incident memory: {incident_id}")
    
    async def _learn_from_incident(
        self,
        incident: IncidentMemory,
        deployment: Optional[DeploymentEvent]
    ):
        """
        Extract learnings from incident.
        Update pattern confidence scores.
        """
        if not deployment:
            return
        
        # Find or create pattern memories
        for pattern in incident.patterns:
            result = await self.db.execute(
                select(PatternMemory)
                .where(PatternMemory.pattern_type == pattern)
            )
            
            pattern_memory = result.scalar_one_or_none()
            
            if pattern_memory:
                # Update existing pattern
                pattern_memory.occurrence_count += 1
                pattern_memory.confidence = min(
                    pattern_memory.confidence + 0.05,
                    0.99
                )
                pattern_memory.last_seen = datetime.utcnow()
            else:
                # Create new pattern
                pattern_memory = PatternMemory(
                    pattern_type=pattern,
                    description=f"Pattern: {pattern}",
                    occurrence_count=1,
                    confidence=0.6,
                    typical_impact=incident.severity,
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow()
                )
                self.db.add(pattern_memory)
        
        await self.db.commit()
        
        logger.info(f"Learned from incident: Updated patterns")
    
    async def monitor_deployment_health(
        self,
        deployment_id: str,
        current_logs: List[Dict],
        duration_minutes: int = 30
    ) -> Dict:
        """
        Post-deployment health monitoring.
        
        Compares current logs against baseline to detect deployment-induced issues.
        
        Args:
            deployment_id: Deployment to monitor
            current_logs: Recent logs from the system
            duration_minutes: How long deployment has been running
            
        Returns:
            Health assessment with rollback recommendation if needed
        """
        # Find the deployment
        result = await self.db.execute(
            select(DeploymentEvent)
            .where(DeploymentEvent.deployment_id == deployment_id)
        )
        deployment = result.scalar_one_or_none()
        
        if not deployment:
            return {"error": "Deployment not found"}
        
        # Get baseline from before deployment
        baseline = deployment.system_state or {}
        baseline_error_rate = baseline.get("error_rate", 0.0)
        
        # Analyze current logs
        current_analysis = await self.log_analyzer.analyze_logs(current_logs)
        current_error_rate = current_analysis.get("error_rate", 0.0)
        
        # Calculate degradation
        error_rate_increase = current_error_rate - baseline_error_rate
        degradation_percent = (error_rate_increase / max(baseline_error_rate, 0.01)) * 100
        
        # Extract new error patterns (errors that weren't there before)
        new_patterns = await self._detect_new_error_patterns(
            current_logs,
            deployment.commit_sha
        )
        
        # Determine health status
        health_status = self._assess_deployment_health(
            error_rate_increase,
            degradation_percent,
            new_patterns,
            current_analysis.get("anomalies", [])
        )
        
        # Should we rollback?
        rollback_recommendation = self._should_rollback(
            health_status,
            deployment,
            duration_minutes
        )
        
        result = {
            "deployment_id": deployment_id,
            "commit_sha": deployment.commit_sha,
            "monitoring_duration": f"{duration_minutes} minutes",
            "baseline": {
                "error_rate": baseline_error_rate,
                "health_score": baseline.get("health_score", 1.0)
            },
            "current": {
                "error_rate": current_error_rate,
                "error_count": current_analysis.get("error_count", 0),
                "anomalies": current_analysis.get("anomalies", [])
            },
            "changes": {
                "error_rate_increase": round(error_rate_increase, 4),
                "degradation_percent": round(degradation_percent, 1),
                "new_error_patterns": new_patterns
            },
            "health_status": health_status,
            "rollback": rollback_recommendation
        }
        
        # Record if deployment resulted in incident
        if health_status in ["CRITICAL", "UNHEALTHY"]:
            await self._mark_deployment_unhealthy(deployment, result)
        
        return result
    
    async def _detect_new_error_patterns(
        self,
        current_logs: List[Dict],
        commit_sha: str
    ) -> List[str]:
        """
        Detect error patterns that appeared AFTER deployment.
        """
        new_patterns = []
        
        error_logs = [
            log for log in current_logs 
            if log.get("level", "").lower() in ["error", "critical"]
        ]
        
        for log in error_logs:
            message = log.get("message", "").lower()
            
            # Check for error patterns
            if "auth" in message and "failed" in message:
                new_patterns.append("auth_failure")
            elif "database" in message and ("timeout" in message or "connection" in message):
                new_patterns.append("database_connection")
            elif "null" in message or "undefined" in message:
                new_patterns.append("null_reference")
            elif "memory" in message or "heap" in message:
                new_patterns.append("memory_leak")
            elif "429" in message or "rate limit" in message:
                new_patterns.append("rate_limit")
            elif "500" in message or "internal server" in message:
                new_patterns.append("server_error")
        
        return list(set(new_patterns))
    
    def _assess_deployment_health(
        self,
        error_rate_increase: float,
        degradation_percent: float,
        new_patterns: List[str],
        anomalies: List[Dict]
    ) -> str:
        """
        Assess deployment health based on metrics.
        
        Returns: HEALTHY | DEGRADED | UNHEALTHY | CRITICAL
        """
        # Critical: Major error rate spike or multiple new patterns
        if error_rate_increase > 0.2 or len(new_patterns) >= 3:
            return "CRITICAL"
        
        # Unhealthy: Significant degradation
        if error_rate_increase > 0.1 or degradation_percent > 100:
            return "UNHEALTHY"
        
        # Degraded: Minor issues detected
        if error_rate_increase > 0.05 or len(new_patterns) > 0 or len(anomalies) > 0:
            return "DEGRADED"
        
        return "HEALTHY"
    
    def _should_rollback(
        self,
        health_status: str,
        deployment: DeploymentEvent,
        duration_minutes: int
    ) -> Dict:
        """
        Determine if rollback is recommended.
        """
        if health_status == "CRITICAL":
            return {
                "recommended": True,
                "urgency": "IMMEDIATE",
                "reason": "Critical errors detected - immediate rollback required",
                "action": "Execute rollback now"
            }
        
        if health_status == "UNHEALTHY":
            # If high risk deployment showing issues, rollback faster
            if deployment.predicted_risk >= 0.7:
                return {
                    "recommended": True,
                    "urgency": "HIGH",
                    "reason": "High-risk deployment showing degradation",
                    "action": "Rollback within 15 minutes if not improving"
                }
            else:
                return {
                    "recommended": True,
                    "urgency": "MEDIUM",
                    "reason": "Deployment health degraded",
                    "action": "Monitor closely, prepare rollback"
                }
        
        if health_status == "DEGRADED":
            return {
                "recommended": False,
                "urgency": "LOW",
                "reason": "Minor issues detected",
                "action": "Continue monitoring, investigate errors"
            }
        
        return {
            "recommended": False,
            "urgency": "NONE",
            "reason": "Deployment healthy",
            "action": "Continue normal monitoring"
        }
    
    async def _mark_deployment_unhealthy(
        self,
        deployment: DeploymentEvent,
        health_result: Dict
    ):
        """Mark deployment as unhealthy in database for learning."""
        # Update would happen here but SQLAlchemy ORM update pattern
        # We'll create an incident record instead
        
        incident = IncidentMemory(
            incident_id=f"auto-{deployment.deployment_id}",
            severity="P2" if health_result["health_status"] == "DEGRADED" else "P1",
            description=f"Deployment {deployment.deployment_id} health degraded",
            root_cause_commit=deployment.commit_sha,
            occurred_at=datetime.utcnow(),
            time_to_detect_minutes=int(
                health_result.get("monitoring_duration", "0").split()[0]
            ),
            patterns=health_result["changes"].get("new_error_patterns", [])
        )
        
        self.db.add(incident)
        await self.db.commit()
        
        logger.warning(
            f"Deployment {deployment.deployment_id} marked unhealthy - "
            f"auto-incident created"
        )
    
    async def detect_incident_cause(
        self,
        incident_timestamp: datetime,
        error_logs: Optional[List[Dict]] = None
    ) -> Dict:
        """
        When incident happens, trace back to root cause using all signals.
        
        Correlates:
        - Recent commits (last 24 hours)
        - Log patterns and errors
        - Similar historical incidents
        """
        # Look back 24 hours for commits
        recent_commits = await self._get_commits_before(incident_timestamp, hours=24)
        
        # Analyze logs around incident time
        log_patterns = await self._analyze_logs_around(incident_timestamp, error_logs)
        
        # Query historical memory for similar incidents
        similar_incidents = await self._find_similar_incident_patterns(log_patterns)
        
        # ML: Which commit most likely caused this?
        root_cause = await self._predict_root_cause(
            recent_commits, 
            log_patterns,
            similar_incidents
        )
        
        return {
            "incident_timestamp": incident_timestamp.isoformat(),
            "likely_root_cause": root_cause,
            "recent_commits": recent_commits,
            "log_evidence": log_patterns,
            "similar_past_incidents": similar_incidents,
            "confidence": root_cause.get("confidence", 0.0) if root_cause else 0.0
        }
    
    async def _get_commits_before(
        self, 
        timestamp: datetime, 
        hours: int = 24
    ) -> List[Dict]:
        """Get commits deployed before the incident."""
        time_window = timestamp - timedelta(hours=hours)
        
        result = await self.db.execute(
            select(CommitMemory)
            .where(CommitMemory.committed_at >= time_window)
            .where(CommitMemory.committed_at <= timestamp)
            .order_by(CommitMemory.committed_at.desc())
        )
        
        commits = result.scalars().all()
        
        return [
            {
                "sha": commit.sha,
                "author": commit.author,
                "risk_score": commit.risk_score,
                "patterns": commit.risky_patterns,
                "committed_at": commit.committed_at.isoformat()
            }
            for commit in commits
        ]
    
    async def _analyze_logs_around(
        self,
        incident_timestamp: datetime,
        error_logs: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Analyze logs around incident time.
        Extract patterns, error types, affected services.
        """
        if error_logs:
            analysis = await self.log_analyzer.analyze_logs(error_logs)
            
            # Extract patterns from error messages
            patterns = []
            for log in error_logs:
                message = log.get("message", "").lower()
                
                if "auth" in message or "permission" in message:
                    patterns.append("auth_failure")
                elif "timeout" in message or "connection" in message:
                    patterns.append("connection_issue")
                elif "database" in message or "sql" in message:
                    patterns.append("database_error")
                elif "memory" in message or "oom" in message:
                    patterns.append("memory_issue")
                elif "500" in message or "internal server" in message:
                    patterns.append("server_error")
            
            return {
                "error_count": analysis.get("error_count", 0),
                "error_rate": analysis.get("error_rate", 0.0),
                "patterns": list(set(patterns)),
                "anomalies": analysis.get("anomalies", [])
            }
        
        return {
            "error_count": 0,
            "error_rate": 0.0,
            "patterns": [],
            "anomalies": []
        }
    
    async def _find_similar_incident_patterns(self, log_patterns: Dict) -> List[Dict]:
        """Find historical incidents with similar log patterns."""
        if not log_patterns.get("patterns"):
            return []
        
        # Query incidents with overlapping patterns
        result = await self.db.execute(
            select(IncidentMemory)
            .where(IncidentMemory.occurred_at >= datetime.utcnow() - timedelta(days=90))
            .order_by(IncidentMemory.occurred_at.desc())
            .limit(20)
        )
        
        incidents = result.scalars().all()
        
        similar = []
        for incident in incidents:
            incident_patterns = set(incident.patterns or [])
            log_pattern_set = set(log_patterns.get("patterns", []))
            
            # Calculate pattern overlap
            overlap = len(incident_patterns & log_pattern_set)
            if overlap > 0:
                similar.append({
                    "incident_id": incident.incident_id,
                    "severity": incident.severity,
                    "root_cause_commit": incident.root_cause_commit,
                    "occurred_at": incident.occurred_at.isoformat(),
                    "pattern_overlap": overlap,
                    "patterns": incident.patterns
                })
        
        return sorted(similar, key=lambda x: x["pattern_overlap"], reverse=True)[:5]
    
    async def _predict_root_cause(
        self,
        recent_commits: List[Dict],
        log_patterns: Dict,
        similar_incidents: List[Dict]
    ) -> Optional[Dict]:
        """
        Use ML to predict which commit caused the incident.
        
        Scoring based on:
        - Pattern match between commit and logs
        - Commit risk score
        - Time proximity (recent commits more likely)
        - Historical evidence (similar incidents)
        """
        if not recent_commits:
            return None
        
        scored_commits = []
        log_pattern_set = set(log_patterns.get("patterns", []))
        
        for commit in recent_commits:
            score = 0.0
            
            # Pattern matching (40% weight)
            commit_patterns = set(commit.get("patterns", []))
            pattern_overlap = len(commit_patterns & log_pattern_set)
            score += pattern_overlap * 0.4
            
            # Commit risk score (30% weight)
            score += (commit.get("risk_score", 0) / 10) * 0.3
            
            # Historical evidence (30% weight)
            for similar in similar_incidents:
                if similar.get("root_cause_commit") == commit["sha"]:
                    score += 0.3
                    break
            
            scored_commits.append({
                "commit": commit,
                "score": score,
                "confidence": min(score, 0.95)
            })
        
        # Return highest scoring commit
        if scored_commits:
            best_match = max(scored_commits, key=lambda x: x["score"])
            return {
                "sha": best_match["commit"]["sha"],
                "author": best_match["commit"]["author"],
                "risk_score": best_match["commit"]["risk_score"],
                "matched_patterns": list(
                    set(best_match["commit"].get("patterns", [])) & log_pattern_set
                ),
                "confidence": best_match["confidence"],
                "committed_at": best_match["commit"]["committed_at"]
            }
        
        return None
