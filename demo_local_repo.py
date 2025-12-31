import asyncio
import os
import sys
import json
from datetime import datetime
from typing import Dict

# Add src to path
sys.path.append(os.getcwd())

from src.services.intelligence_engine import IntelligenceEngine
from src.services.github_enrichment import GitHubEnrichmentService
from src.services.log_analyzer import LogAnalyzer
from src.services.trace_analyzer import TraceAnalyzer
from src.config import settings

# ANSI Colors for professional terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

async def run_demo(repo_path: str = "."):
    """
    Run RootOps Intelligence Engine on a local repository.
    """
    print(f"{Colors.HEADER}{Colors.BOLD}RootOps Intelligence Engine - Local Analysis{Colors.ENDC}")
    print(f"{Colors.BLUE}Target Repository: {os.path.abspath(repo_path)}{Colors.ENDC}")
    
    # Check for LLM API Key
    if not settings.LLM_API_KEY:
        print(f"{Colors.WARNING}[WARN] LLM_API_KEY not found. Semantic analysis disabled.{Colors.ENDC}")
    else:
        print(f"{Colors.GREEN}[OK] Semantic Analysis Enabled (Provider: {settings.LLM_PROVIDER}){Colors.ENDC}")

    # Initialize Services
    print("Initializing Intelligence Engine...")
    
    # Mock DB for demo
    from unittest.mock import AsyncMock
    mock_db = AsyncMock()
    
    github_service = GitHubEnrichmentService()
    log_analyzer = LogAnalyzer()
    trace_analyzer = TraceAnalyzer()
    
    engine = IntelligenceEngine(
        db_session=mock_db,
        github_service=github_service,
        log_analyzer=log_analyzer,
        trace_analyzer=trace_analyzer
    )
    
    # Get latest commit from local git
    try:
        import git
        repo = git.Repo(repo_path)
        latest_commit = repo.head.commit
        print(f"Analyzing commit: {Colors.CYAN}{latest_commit.hexsha[:8]}{Colors.ENDC}")
        print(f"Message: {latest_commit.summary}")
    except Exception as e:
        print(f"{Colors.FAIL}[ERROR] Failed to read git repo: {e}{Colors.ENDC}")
        return

    # Simulate System Context
    system_state = {
        "cpu_usage": 45.0,
        "memory_usage": 60.0,
        "error_rate": 0.001,
        "log_count": 500,
        "health_score": 0.95
    }
    
    context = {
        "commit": {
            "sha": latest_commit.hexsha,
            "message": latest_commit.message,
            "timestamp": latest_commit.committed_datetime,
            "author": latest_commit.author.name,
            "email": latest_commit.author.email,
            "files_changed": len(latest_commit.stats.files),
            "additions": latest_commit.stats.total['insertions'],
            "deletions": latest_commit.stats.total['deletions']
        },
        "system_state": system_state,
        "memory": {"similar_incidents": [], "file_incidents": []}
    }

    print("\nRunning Analysis...")
    start_time = datetime.now()
    
    try:
        # 1. Enrich Commit (triggers LLM)
        enriched_commit = await engine._analyze_commit(latest_commit.hexsha, "local/repo")
        context["commit"].update(enriched_commit)
        
        # 2. Predict Outcome (triggers XGBoost)
        prediction = await engine._predict_outcome(context)
        
        duration = (datetime.now() - start_time).total_seconds()
        print(f"{Colors.GREEN}Analysis Complete in {duration:.2f}s{Colors.ENDC}\n")
        
        # --- REPORT ---
        print(f"{Colors.HEADER}=== INTELLIGENCE REPORT ==={Colors.ENDC}")
        
        risk_score = enriched_commit.get("risk_score", 0)
        risk_color = Colors.GREEN if risk_score < 4 else (Colors.WARNING if risk_score < 7 else Colors.FAIL)
        print(f"Risk Score: {risk_color}{risk_score:.1f}/10{Colors.ENDC}")
        
        prob = prediction["probability"] * 100
        print(f"Incident Probability: {risk_color}{prob:.1f}%{Colors.ENDC}")
        
        if "predicted_p95_latency" in prediction and prediction["predicted_p95_latency"]:
             print(f"Predicted Latency: {prediction['predicted_p95_latency']:.0f}ms")
             
        if "llm_analysis" in enriched_commit:
            print(f"\n{Colors.BOLD}Semantic Insight ({settings.LLM_PROVIDER}):{Colors.ENDC}")
            llm = enriched_commit["llm_analysis"]
            print(f"Summary: {llm.get('summary')}")
            print(f"Breaking Change: {llm.get('breaking_change')}")
            print(f"Action: {llm.get('suggested_action')}")
            
        print(f"\n{Colors.BOLD}Recommendations:{Colors.ENDC}")
        recs = engine._generate_recommendations(context, prediction)
        for rec in recs:
            print(f"- {rec}")
            
        print(f"\n{Colors.HEADER}==========================={Colors.ENDC}")

    except Exception as e:
        print(f"{Colors.FAIL}Analysis Failed: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    asyncio.run(run_demo(path))
