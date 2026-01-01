"""
Auto-polling background workers.

Continuously monitors GitHub, logs, and metrics without requiring manual API calls.
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from src.config import settings
from src.services.github_enrichment import GitHubEnrichmentService
from src.integrations.detector import BackendDetector
from src.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class AutoPoller:
    """
    Background workers that automatically gather intelligence.
    
    Users don't need to call APIs manually - RootOps continuously learns.
    """
    
    def __init__(self):
        self.github_service = GitHubEnrichmentService()
        self.backend_detector = BackendDetector()
        self.running = False
        self.last_commit_sha: Optional[str] = None
    
    async def start(self):
        """Start all background workers"""
        logger.info("Starting auto-polling background workers...")
        
        # Detect available backends
        detected = await self.backend_detector.detect()
        logger.info(f"Detected backends: {detected}")
        
        self.running = True
        
        # Start workers
        tasks = [
            asyncio.create_task(self._poll_github_commits()),
        ]
        
        if detected["logs"] != "none":
            tasks.append(asyncio.create_task(self._monitor_logs()))
        
        logger.info(f"Started {len(tasks)} background workers")
        
        # Keep workers running
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def stop(self):
        """Stop all workers"""
        logger.info("Stopping background workers...")
        self.running = False
    
    async def _poll_github_commits(self):
        """
        Poll GitHub for new commits every 5 minutes.
        Automatically analyze new commits.
        """
        logger.info("GitHub commit poller started")
        
        while self.running:
            try:
                if not settings.GITHUB_REPO or not settings.GITHUB_TOKEN:
                    logger.warning("GitHub not configured - skipping commit polling")
                    await asyncio.sleep(300)
                    continue
                
                # Fetch latest commits
                commits = await self._fetch_recent_commits(limit=10)
                
                # Analyze new commits
                for commit_sha in commits:
                    if commit_sha == self.last_commit_sha:
                        break  # Already processed
                    
                    await self._analyze_commit(commit_sha)
                
                if commits:
                    self.last_commit_sha = commits[0]
                
            except Exception as e:
                logger.error(f"Error in GitHub poller: {e}")
            
            # Poll every 5 minutes
            await asyncio.sleep(300)
    
    async def _monitor_logs(self):
        """
        Monitor logs every 2 minutes.
        Detect anomalies and correlate with recent commits.
        """
        logger.info("Log monitor started")
        
        while self.running:
            try:
                # Fetch recent logs
                logs = await self.backend_detector.get_logs(since_minutes=5)
                
                if logs:
                    # Analyze for anomalies
                    await self._analyze_logs(logs)
                    
                    # Check for deployment issues
                    await self._check_deployment_health(logs)
                
            except Exception as e:
                logger.error(f"Error in log monitor: {e}")
            
            # Monitor every 2 minutes
            await asyncio.sleep(120)
    
    async def _fetch_recent_commits(self, limit: int = 10) -> list:
        """Fetch recent commits from GitHub"""
        import httpx
        
        url = f"https://api.github.com/repos/{settings.GITHUB_REPO}/commits"
        headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=headers,
                    params={"per_page": limit},
                    timeout=10.0
                )
                response.raise_for_status()
                
                commits = response.json()
                return [c["sha"] for c in commits]
        
        except Exception as e:
            logger.error(f"Failed to fetch commits: {e}")
            return []
    
    async def _analyze_commit(self, commit_sha: str):
        """Analyze a commit using Intelligence Engine"""
        async with AsyncSessionLocal() as db:
            try:
                from src.services.intelligence_engine import IntelligenceEngine
                from src.services.log_analyzer import LogAnalyzer
                from src.services.trace_analyzer import TraceAnalyzer
                
                engine = IntelligenceEngine(
                    db_session=db,
                    github_service=self.github_service,
                    log_analyzer=LogAnalyzer(),
                    trace_analyzer=TraceAnalyzer()
                )
                
                result = await engine.analyze_deployment(
                    commit_sha=commit_sha,
                    repository=settings.GITHUB_REPO,
                    deployment_id=f"auto-{commit_sha[:8]}"
                )
                
                # Log high-risk commits
                if result["prediction"]["incident_probability"] >= 0.7:
                    logger.warning(
                        f"HIGH RISK COMMIT DETECTED: {commit_sha[:8]} "
                        f"(probability: {result['prediction']['incident_probability']:.2f}) "
                        f"- {result['action']}"
                    )
                else:
                    logger.info(
                        f"Analyzed commit {commit_sha[:8]}: "
                        f"risk={result['analysis']['risk_score']:.1f}, "
                        f"action={result['action']}"
                    )
                
            except Exception as e:
                logger.error(f"Failed to analyze commit {commit_sha[:8]}: {e}")
    
    async def _analyze_logs(self, logs: list):
        """Analyze logs for anomalies and save to DB"""
        async with AsyncSessionLocal() as db:
            try:
                from src.services.log_analyzer import LogAnalyzer
                from src.models.db_models import LogAnalysis
                
                analyzer = LogAnalyzer()
                result = await analyzer.analyze_logs(logs)
                
                # Save to database
                log_analysis = LogAnalysis(
                    log_count=result["log_count"],
                    error_count=result["error_count"],
                    warning_count=result["warning_count"],
                    anomalies=result["anomalies"],
                    created_at=datetime.utcnow()
                )
                db.add(log_analysis)
                await db.commit()
                
                # Log significant anomalies
                if result.get("anomalies"):
                    logger.warning(
                        f"Log anomalies detected: {len(result['anomalies'])} issues, "
                        f"error_rate={result.get('error_rate', 0):.3f}"
                    )
            except Exception as e:
                logger.error(f"Failed to analyze/save logs: {e}")
                await db.rollback()
    
    async def _check_deployment_health(self, logs: list):
        """Check if recent deployments are healthy"""
        async with AsyncSessionLocal() as db:
            try:
                from src.models.db_models import DeploymentEvent
                from sqlalchemy import select
                
                # Get deployments from last hour
                one_hour_ago = datetime.utcnow() - timedelta(hours=1)
                
                result = await db.execute(
                    select(DeploymentEvent)
                    .where(DeploymentEvent.deployed_at >= one_hour_ago)
                    .where(DeploymentEvent.resulted_in_incident == False)
                    .order_by(DeploymentEvent.deployed_at.desc())
                    .limit(5)
                )
                
                deployments = result.scalars().all()
                
                # Monitor each recent deployment
                for deployment in deployments:
                    # Calculate how long deployment has been running
                    duration = datetime.utcnow() - deployment.deployed_at
                    duration_minutes = int(duration.total_seconds() / 60)
                    
                    if duration_minutes < 60:  # Monitor first hour
                        from src.services.intelligence_engine import IntelligenceEngine
                        from src.services.log_analyzer import LogAnalyzer
                        from src.services.trace_analyzer import TraceAnalyzer
                        
                        engine = IntelligenceEngine(
                            db_session=db,
                            github_service=self.github_service,
                            log_analyzer=LogAnalyzer(),
                            trace_analyzer=TraceAnalyzer()
                        )
                        
                        health = await engine.monitor_deployment_health(
                            deployment_id=deployment.deployment_id,
                            current_logs=logs,
                            duration_minutes=duration_minutes
                        )
                        
                        # Alert on critical issues
                        if health.get("health_status") in ["CRITICAL", "UNHEALTHY"]:
                            logger.error(
                                f"DEPLOYMENT HEALTH ISSUE: {deployment.deployment_id} "
                                f"status={health['health_status']}, "
                                f"rollback_recommended={health['rollback']['recommended']}"
                            )
            
            except Exception as e:
                logger.error(f"Failed to check deployment health: {e}")
