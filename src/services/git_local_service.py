"""
Local Git integration for commit analysis

Uses gitpython to analyze the local repository when GitHub API is unavailable.
"""
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
import git
from src.services.github_enrichment import GitHubEnrichmentService, CommitStats

logger = logging.getLogger(__name__)

class GitLocalService:
    """Analyze local git repository for commit data."""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self._enrichment_service = GitHubEnrichmentService() # Reuse logic helpers
        try:
            self.repo = git.Repo(repo_path, search_parent_directories=True)
            logger.info(f"GitLocalService initialized for: {self.repo.working_dir}")
        except Exception as e:
            logger.warning(f"Failed to initialize GitLocalService: {e}")
            self.repo = None

    def get_commit_details(self, commit_sha: str) -> Optional[CommitStats]:
        """Fetch details from local git."""
        if not self.repo:
            return None
            
        try:
            commit = self.repo.commit(commit_sha)
            
            # Get stats
            stats = commit.stats.total
            files_stats = commit.stats.files
            
            # Build file list in expected format
            files_data = []
            for filename, file_stat in files_stats.items():
                files_data.append({
                    "filename": filename,
                    "additions": file_stat.get("insertions", 0),
                    "deletions": file_stat.get("deletions", 0),
                    # We can't easily get patch/diff content without more work, 
                    # but for basic pattern matching filename is enough.
                    # For semantic analysis, we might want to get the diff.
                })

            commit_data = {
                "sha": commit.hexsha,
                "message": commit.message.strip(),
                "author": commit.author.name,
                "email": commit.author.email,
                "timestamp": datetime.fromtimestamp(commit.committed_date, tz=timezone.utc),
                "files_changed": len(files_data),
                "additions": stats["insertions"],
                "deletions": stats["deletions"],
                "total_changes": stats["lines"],
                "files": files_data,
                "risk_score": 0.0,
                "complexity_score": 0.0,
                "blast_radius": 0,
                "test_ratio": 0.0,
                "commit_type": "unknown"
            }
            
            # Reuse logic from GitHub service for consistency
            commit_data["test_ratio"] = self._enrichment_service._calculate_test_ratio(files_data)
            commit_data["blast_radius"] = self._enrichment_service._calculate_blast_radius(files_data)
            commit_data["complexity_score"] = self._enrichment_service._calculate_complexity(commit_data, files_data)
            commit_data["risk_score"] = self._enrichment_service._calculate_risk_score(commit_data)
            commit_data["commit_type"] = self._enrichment_service.classify_commit_type(commit_data["message"])
            
            return CommitStats(**commit_data)

        except Exception as e:
            logger.error(f"Local git analysis failed for {commit_sha}: {e}")
            return None

    def extract_risky_patterns(self, files: List[Dict]) -> List[str]:
        """Proxy to GitHub service for consistency."""
        return self._enrichment_service.extract_risky_patterns(files)

    def get_author_history(self, author_email: str, days: int = 90) -> Dict:
        """Get author history from local git log."""
        if not self.repo:
            return {"total_commits": 0, "avg_files_changed": 0, "recent_activity": 0}

        try:
            # Calculate date threshold
            since_date = datetime.now() - timedelta(days=days)
            
            # Get commits by author
            commits = list(self.repo.iter_commits(
                since=since_date,
                author=author_email
            ))
            
            total_files = 0
            for c in commits:
                total_files += len(c.stats.files)

            return {
                "total_commits": len(commits),
                "avg_files_changed": total_files / len(commits) if commits else 0,
                "recent_activity": len(commits)
            }
        except Exception as e:
            logger.error(f"Failed to get local author history: {e}")
            return {"total_commits": 0, "avg_files_changed": 0, "recent_activity": 0}

    def get_commit_diff(self, commit_sha: str) -> Optional[str]:
        """Get the text diff of the commit."""
        if not self.repo:
            return None
            
        try:
            commit = self.repo.commit(commit_sha)
            # Compare with parent to get diff
            if commit.parents:
                parent = commit.parents[0]
                diff = self.repo.git.diff(parent.hexsha, commit.hexsha)
            else:
                # Initial commit
                diff = self.repo.git.show(commit.hexsha)
            return diff
        except Exception as e:
            logger.error(f"Failed to get diff for {commit_sha}: {e}")
            return None
