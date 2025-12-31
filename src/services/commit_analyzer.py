"""
Commit analysis service

Analyzes git commits for breaking changes and code quality issues.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import logging
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
        
        if not github_data:
            # Fallback to local git analysis
            try:
                from src.services.git_local_service import GitLocalService
                local_git = GitLocalService()
                github_data = local_git.get_commit_details(commit_hash)
                
                if github_data:
                    logger.info(f"Used local git analysis for {commit_hash}")
                    
                    # Get author risk profile from local git
                    author_history = local_git.get_author_history(github_data.email)
                else:
                    logger.warning(f"Local git analysis failed for {commit_hash}")
                    # If both fail, we essentially return a "not found" or minimal/empty struct 
                    # rather than fake data, to maintain trust.
                    return {
                        "repository": repository,
                        "commit_hash": commit_hash,
                        "error": "Could not analyze commit (GitHub API and local git unavailable)",
                        "risk_score": 5.0, # Default medium risk for unknown changes
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

            except Exception as e:
                logger.error(f"Fallback analysis failed: {e}")
                return {
                    "repository": repository,
                    "commit_hash": commit_hash,
                    "error": str(e),
                    "risk_score": 5.0,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

        # Common processing for both GitHub and Local data
        
        # Use real data (either from GitHub or Local)
        changed_files = github_data.files_changed
        lines_added = github_data.additions
        lines_deleted = github_data.deletions
        risky_patterns = self.github_service.extract_risky_patterns(github_data.files)
        
        # If we didn't populate author history from local git yet and it's from GitHub, fetch it
        # (The GitHub block above doesn't fetch history, so we might need to here if not done)
        # However, the original code fetched it inside the 'if github_data' block.
        # Let's standardize: if we have github_data, we assume we might need author history.
        
        # Note: In the local branch above, I fetched author_history. 
        # In the GitHub case, I need to fetch it if I haven't.
        # But 'github_data' variable is now used for both.
        # So I should handle the GitHub-origin author history here if needed, 
        # or just refactor.
        
        # To keep it simple and correct:
        if not 'author_history' in locals():
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
            "author_commits_90d": author_history.get("total_commits", 0),
            "author_avg_files": round(author_history.get("avg_files_changed", 0), 2),
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
