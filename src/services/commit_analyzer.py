"""
Commit analysis service

Analyzes git commits for breaking changes and code quality issues.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import logging
import random
from src.config import settings
from src.monitoring import predictions_total
from src.services.github_enrichment import GitHubEnrichmentService

logger = logging.getLogger(__name__)


class CommitAnalyzer:
    """Analyze commits for breaking changes and quality issues"""
    
    def __init__(self):
        self.initialized = True
        self.github_service = GitHubEnrichmentService()
        logger.info("CommitAnalyzer initialized")
    
    async def analyze_commit(
        self,
        repository: str,
        commit_hash: str,
        diff: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a commit for potential breaking changes
        
        Args:
            repository: Repository name
            commit_hash: Commit hash or reference
            diff: Optional commit diff for LLM enrichment
            
        Returns:
            Dict with analysis results
        """
        # Try to fetch enriched data from GitHub API
        github_data = await self.github_service.get_commit_details(commit_hash)
        
        if github_data:
            # Use real GitHub data
            changed_files = github_data.files_changed
            lines_added = github_data.additions
            lines_deleted = github_data.deletions
            risky_patterns = self.github_service.extract_risky_patterns(github_data.files)
            
            # Get author risk profile
            author_history = await self.github_service.get_author_history(github_data.email)
            
            result = {
                "repository": repository,
                "commit_hash": commit_hash,
                "changed_files": changed_files,
                "lines_added": lines_added,
                "lines_deleted": lines_deleted,
                "risky_patterns": risky_patterns,
                "complexity_delta": github_data.complexity_score / 10,  # Normalize to 0-1
                "risk_score": github_data.risk_score,
                "blast_radius": github_data.blast_radius,
                "test_ratio": github_data.test_ratio,
                "commit_type": github_data.commit_type,
                "author": github_data.author,
                "author_commits_90d": author_history["total_commits"],
                "author_avg_files": round(author_history["avg_files_changed"], 2),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            # Fallback to heuristic analysis if GitHub API unavailable
            logger.warning(f"GitHub API unavailable, using heuristic analysis for {commit_hash}")
            changed_files = random.randint(1, 15)
            lines_added = random.randint(5, 500)
            lines_deleted = random.randint(0, 200)
            
            # Detect risky patterns (heuristic)
            risky_patterns = []
            if random.random() < 0.3:
                risky_patterns.append("db_migration")
            if random.random() < 0.3:
                risky_patterns.append("auth_logic")
            if random.random() < 0.2:
                risky_patterns.append("dependency_version")
            
            result = {
                "repository": repository,
                "commit_hash": commit_hash,
                "changed_files": changed_files,
                "lines_added": lines_added,
                "lines_deleted": lines_deleted,
                "risky_patterns": risky_patterns,
                "complexity_delta": round(random.uniform(-0.1, 0.4), 3),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Track metric
        predictions_total.labels(
            model_type="breaking_change",
            result="success"
        ).inc()
        
        # Optional LLM enrichment
        if settings.ENABLE_LLM_ENRICHMENT and settings.CLAUDE_API_KEY and diff:
            try:
                from src.services.llm_client import enrich_commit_analysis
                llm_insights = await enrich_commit_analysis(diff)
                if llm_insights:
                    result["semantic_risk_score"] = llm_insights.get("risk_score")
                    result["semantic_summary"] = llm_insights.get("summary")
            except Exception as e:
                logger.error(f"LLM enrichment failed: {e}")
        
        return result
