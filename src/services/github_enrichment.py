"""
GitHub API integration for enriched commit analysis

Fetches detailed commit data from GitHub API including:
- File changes and statistics
- Author information
- Code churn metrics
- Risk indicators
"""
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CommitStats(BaseModel):
    """Detailed commit statistics from GitHub API."""
    sha: str
    message: str
    author: str
    email: str
    timestamp: datetime
    files_changed: int
    additions: int
    deletions: int
    total_changes: int
    files: List[Dict]
    risk_score: float
    complexity_score: float
    blast_radius: int
    test_ratio: float
    commit_type: str


class GitHubEnrichmentService:
    """Enriches commits with detailed GitHub API data for ML analysis."""
    
    def __init__(self, token: Optional[str] = None, repo: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.repo = repo or os.getenv("GITHUB_REPO")
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"
        
        logger.info(f"GitHubEnrichmentService initialized for repo: {self.repo}")
    
    async def get_commit_details(self, commit_sha: str) -> Optional[CommitStats]:
        """Fetch detailed commit data from GitHub API."""
        if not self.repo or not self.token:
            logger.warning("GitHub integration not configured (missing GITHUB_TOKEN or GITHUB_REPO)")
            return None
        
        url = f"{self.base_url}/repos/{self.repo}/commits/{commit_sha}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=10.0)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract file statistics
                files = data.get("files", [])
                stats = data.get("stats", {})
                
                commit_data = {
                    "sha": commit_sha,
                    "message": data["commit"]["message"],
                    "author": data["commit"]["author"]["name"],
                    "email": data["commit"]["author"]["email"],
                    "timestamp": datetime.fromisoformat(
                        data["commit"]["author"]["date"].replace("Z", "+00:00")
                    ),
                    "files_changed": len(files),
                    "additions": stats.get("additions", 0),
                    "deletions": stats.get("deletions", 0),
                    "total_changes": stats.get("total", 0),
                    "files": files,
                    "risk_score": 0.0,
                    "complexity_score": 0.0,
                    "blast_radius": 0,
                    "test_ratio": 0.0,
                    "commit_type": "unknown"
                }
                
                # Calculate ML features
                commit_data["test_ratio"] = self._calculate_test_ratio(files)
                commit_data["blast_radius"] = self._calculate_blast_radius(files)
                commit_data["complexity_score"] = self._calculate_complexity(commit_data, files)
                commit_data["risk_score"] = self._calculate_risk_score(commit_data)
                commit_data["commit_type"] = self.classify_commit_type(commit_data["message"])
                
                logger.info(f"Fetched GitHub commit details for {commit_sha[:8]}: "
                           f"{commit_data['files_changed']} files, "
                           f"risk={commit_data['risk_score']:.2f}")
                
                return CommitStats(**commit_data)
                
        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API error for commit {commit_sha}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch GitHub commit details: {e}")
            return None
    
    def _calculate_risk_score(self, commit_data: Dict) -> float:
        """Calculate risk score based on commit characteristics."""
        score = 0.0
        
        # File count factor (0-3 points)
        file_count = commit_data["files_changed"]
        score += min(file_count / 10, 3.0)
        
        # Code churn factor (0-3 points)
        churn = commit_data["total_changes"]
        score += min(churn / 200, 3.0)
        
        # Test coverage factor (0-2 points)
        test_ratio = commit_data["test_ratio"]
        score += (1 - test_ratio) * 2.0
        
        # Weekend/night commit factor (0-2 points)
        hour = commit_data["timestamp"].hour
        weekday = commit_data["timestamp"].weekday()
        if weekday >= 5 or hour < 6 or hour > 22:
            score += 2.0
        
        return min(score, 10.0)  # Cap at 10
    
    def _calculate_complexity(self, commit_data: Dict, files: List[Dict]) -> float:
        """Calculate complexity based on changes."""
        # Count different file types
        extensions = set(
            f["filename"].split(".")[-1] 
            for f in files 
            if "." in f["filename"]
        )
        
        # Complexity factors
        complexity = (
            len(files) * 0.5 +                    # Multiple files
            len(extensions) * 0.3 +               # Multiple languages
            commit_data["total_changes"] / 100 +  # Large changes
            self._directory_depth(files) * 0.2    # Deep directory changes
        )
        
        return min(complexity, 10.0)
    
    def _calculate_blast_radius(self, files: List[Dict]) -> int:
        """Calculate how many modules/directories are affected."""
        directories = set()
        for file in files:
            path_parts = file["filename"].split("/")[:-1]
            if path_parts:
                directories.add("/".join(path_parts))
        return len(directories)
    
    def _calculate_test_ratio(self, files: List[Dict]) -> float:
        """Calculate ratio of test files to total files."""
        if not files:
            return 0.0
        
        test_files = sum(
            1 for f in files 
            if "test" in f["filename"].lower() or f["filename"].startswith("tests/")
        )
        
        return test_files / len(files)
    
    def _directory_depth(self, files: List[Dict]) -> int:
        """Calculate average directory depth of changed files."""
        if not files:
            return 0
        
        depths = [f["filename"].count("/") for f in files]
        return sum(depths) // len(depths) if depths else 0
    
    async def get_author_history(self, author_email: str, days: int = 90) -> Dict:
        """Get author's commit history for risk profiling."""
        if not self.repo or not self.token:
            return {"total_commits": 0, "avg_files_changed": 0, "recent_activity": 0}
        
        url = f"{self.base_url}/repos/{self.repo}/commits"
        since = (datetime.now() - timedelta(days=days)).isoformat()
        params = {
            "author": author_email,
            "since": since,
            "per_page": 100
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, 
                    headers=self.headers, 
                    params=params,
                    timeout=10.0
                )
                response.raise_for_status()
                
                commits = response.json()
                
                total_files = sum(len(c.get("files", [])) for c in commits)
                
                return {
                    "total_commits": len(commits),
                    "avg_files_changed": total_files / len(commits) if commits else 0,
                    "recent_activity": len(commits)
                }
        except Exception as e:
            logger.error(f"Failed to fetch author history: {e}")
            return {"total_commits": 0, "avg_files_changed": 0, "recent_activity": 0}
    
    def classify_commit_type(self, message: str) -> str:
        """Classify commit based on message keywords."""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["fix", "bug", "hotfix", "patch"]):
            return "bugfix"
        elif any(word in message_lower for word in ["feat", "feature", "add"]):
            return "feature"
        elif any(word in message_lower for word in ["refactor", "cleanup", "improve"]):
            return "refactor"
        elif any(word in message_lower for word in ["test", "spec"]):
            return "test"
        elif any(word in message_lower for word in ["doc", "readme"]):
            return "documentation"
        else:
            return "other"
    
    def extract_risky_patterns(self, files: List[Dict]) -> List[str]:
        """Extract risky patterns from changed files."""
        patterns = []
        
        for file in files:
            filename = file["filename"].lower()
            
            # Database migrations
            if "migration" in filename or "schema" in filename:
                patterns.append("db_migration")
            
            # Authentication/Authorization
            if "auth" in filename or "login" in filename or "permission" in filename:
                patterns.append("auth_logic")
            
            # Configuration files
            if any(name in filename for name in ["config", "settings", ".env", "dockerfile"]):
                patterns.append("config_change")
            
            # Dependencies
            if any(name in filename for name in ["requirements.txt", "package.json", "go.mod", "pom.xml"]):
                patterns.append("dependency_version")
            
            # API contracts
            if "api" in filename or "schema" in filename or ".proto" in filename:
                patterns.append("api_contract")
        
        return list(set(patterns))  # Remove duplicates
