"""
Dashboard API routes.

Provides data for the web dashboard.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from src.database import get_db
from src.models.db_models import CommitMemory, DeploymentEvent, LogAnalysis

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/overview")
async def get_dashboard_overview(db: AsyncSession = Depends(get_db)):
    """
    Get dashboard overview data.
    
    Returns:
        - active_deployments: Deployments being monitored
        - avg_incident_probability: Average probability from recent commits
        - total_insights: Total commits analyzed
        - high_risk_commits: List of high-risk commits
        - recent_commits: Last 20 commits analyzed
    """
    
    # Count active deployments (deployed in last 24 hours, no incident)
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    
    active_deployments_result = await db.execute(
        select(func.count(DeploymentEvent.id))
        .where(DeploymentEvent.deployed_at >= twenty_four_hours_ago)
        .where(DeploymentEvent.resulted_in_incident == False)
    )
    active_deployments = active_deployments_result.scalar() or 0
    
    # Get recent commits for stats
    recent_commits_result = await db.execute(
        select(CommitMemory)
        .order_by(CommitMemory.analyzed_at.desc())
        .limit(50)
    )
    recent_commits = recent_commits_result.scalars().all()
    
    # Calculate average incident probability
    if recent_commits:
        avg_prob = sum(c.incident_probability for c in recent_commits) / len(recent_commits)
    else:
        avg_prob = 0.0
    
    # Get total commits analyzed
    total_insights_result = await db.execute(
        select(func.count(CommitMemory.id))
    )
    
    # Get latest System Health (Log Analysis)
    latest_logs_result = await db.execute(
        select(LogAnalysis)
        .order_by(LogAnalysis.created_at.desc())
        .limit(1)
    )
    latest_logs = latest_logs_result.scalar_one_or_none()
    
    system_health = {
        "log_anomalies": latest_logs.anomalies if latest_logs else [],
        "error_rate": latest_logs.error_count / latest_logs.log_count if latest_logs and latest_logs.log_count > 0 else 0,
        "last_checked": latest_logs.created_at.isoformat() if latest_logs else None
    }

    # Find high-risk commits (>70% incident probability)
    high_risk = [
        {
            "commit_sha": c.commit_sha,
            "incident_probability": c.incident_probability,
            "risk_score": c.risk_score,
            "analyzed_at": c.analyzed_at.isoformat()
        }
        for c in recent_commits
        if c.incident_probability >= 0.7
    ]
    
    # Recent commits for display
    commits_display = [
        {
            "commit_sha": c.commit_sha,
            "message": c.message,
            "risk_score": c.risk_score,
            "incident_probability": c.incident_probability,
            "action": c.recommended_action,
            "analyzed_at": c.analyzed_at.isoformat(),
            "prediction": c.prediction_details,
            "analysis": {
                "files": c.files
            }
        }
        for c in recent_commits[:20]
    ]
    
    return {
        "active_deployments": active_deployments,
        "avg_incident_probability": round(avg_prob, 3),
        "total_insights": total_insights,
        "high_risk_commits": high_risk,
        "recent_commits": commits_display,
        "system_health": system_health
    }


@router.get("/commits/{commit_sha}")
async def get_commit_details(commit_sha: str, db: AsyncSession = Depends(get_db)):
    """Get detailed analysis for a specific commit"""
    
    result = await db.execute(
        select(CommitMemory).where(CommitMemory.commit_sha == commit_sha)
    )
    commit = result.scalar_one_or_none()
    
    if not commit:
        return {"error": "Commit not found"}
    
    return {
        "commit_sha": commit.commit_sha,
        "message": commit.message,
        "author": commit.author,
        "repository": commit.repository,
        "risk_score": commit.risk_score,
        "incident_probability": commit.incident_probability,
        "files_changed": commit.files_changed,
        "additions": commit.additions,
        "deletions": commit.deletions,
        "risky_patterns": commit.risky_patterns,
        "recommended_action": commit.recommended_action,
        "analyzed_at": commit.analyzed_at.isoformat(),
        "committed_at": commit.committed_at.isoformat() if commit.committed_at else None
    }


@router.get("/deployments")
async def get_recent_deployments(
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """Get recent deployment events"""
    
    result = await db.execute(
        select(DeploymentEvent)
        .order_by(DeploymentEvent.deployed_at.desc())
        .limit(limit)
    )
    deployments = result.scalars().all()
    
    return {
        "deployments": [
            {
                "deployment_id": d.deployment_id,
                "commit_sha": d.commit_sha,
                "environment": d.environment,
                "predicted_risk": d.predicted_risk,
                "resulted_in_incident": d.resulted_in_incident,
                "deployed_at": d.deployed_at.isoformat(),
                "incident_detected_at": d.incident_detected_at.isoformat() if d.incident_detected_at else None
            }
            for d in deployments
        ]
    }
