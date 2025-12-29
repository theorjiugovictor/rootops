"""
API routes for RootOps Intelligence Engine
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import logging

from src.database import get_db
from src.models.requests import (
    CommitAnalysisRequest,
    CommitAnalysisResponse,
    LogAnalysisRequest,
    LogAnalysisResponse,
    TraceAnalysisRequest,
    TraceAnalysisResponse,
    OptimizationRecommendation,
    IntelligenceRequest,
    IntelligenceResponse,
    IncidentRecordRequest,
    DeploymentMonitorRequest
)
from src.models.db_models import CommitAnalysis, LogAnalysis, TraceAnalysis

logger = logging.getLogger(__name__)

router = APIRouter()


# New Intelligence Engine Endpoint
@router.post("/intelligence/deployment", response_model=IntelligenceResponse)
async def analyze_deployment_intelligence(
    request: IntelligenceRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Comprehensive deployment analysis with full intelligence and learning.
    
    This is the main endpoint that:
    - Analyzes commits with GitHub enrichment
    - Recalls similar past situations
    - Predicts outcomes based on learned patterns
    - Provides actionable recommendations
    - Records everything for continuous learning
    
    - **commit_sha**: Commit hash to analyze
    - **repository**: Repository name
    - **deployment_id**: Optional deployment identifier
    """
    from src.main import app
    
    # Create Intelligence Engine instance with database session
    intelligence_engine = app.state.intelligence_engine_factory(db)
    
    result = await intelligence_engine.analyze_deployment(
        commit_sha=request.commit_sha,
        repository=request.repository,
        deployment_id=request.deployment_id
    )
    
    return IntelligenceResponse(**result)


@router.post("/intelligence/incident")
async def record_incident(
    request: IncidentRecordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Record an incident for continuous learning.
    
    The Intelligence Engine learns from every incident to improve future predictions.
    
    - **incident_id**: Unique incident identifier
    - **severity**: P1, P2, P3, or P4
    - **description**: What happened
    - **root_cause_commit**: Commit that caused the incident (if known)
    - **patterns**: List of patterns involved
    """
    from src.main import app
    
    # Create Intelligence Engine instance with database session
    intelligence_engine = app.state.intelligence_engine_factory(db)
    
    await intelligence_engine.record_incident(
        incident_id=request.incident_id,
        severity=request.severity,
        description=request.description,
        root_cause_commit=request.root_cause_commit,
        patterns=request.patterns
    )
    
    return {
        "status": "recorded",
        "incident_id": request.incident_id,
        "message": "Incident recorded and patterns updated for continuous learning"
    }


@router.post("/intelligence/monitor")
async def monitor_deployment(
    request: DeploymentMonitorRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Post-deployment health monitoring.
    
    Continuously monitors deployment health by comparing current logs
    against baseline. Detects deployment-induced issues and recommends
    rollback if needed.
    
    - **deployment_id**: Deployment to monitor
    - **current_logs**: Recent logs from the system
    - **duration_minutes**: How long deployment has been running
    """
    from src.main import app
    
    intelligence_engine = app.state.intelligence_engine_factory(db)
    
    result = await intelligence_engine.monitor_deployment_health(
        deployment_id=request.deployment_id,
        current_logs=request.current_logs,
        duration_minutes=request.duration_minutes
    )
    
    return result


@router.post("/analyze/commit", response_model=CommitAnalysisResponse)
async def analyze_commit(
    request: CommitAnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze a git commit for breaking changes and code quality issues
    
    - **repository**: Repository name
    - **commit_hash**: Commit hash or reference
    - **diff**: Optional commit diff for LLM enrichment
    """
    from src.main import app
    
    analyzer = app.state.commit_analyzer
    result = await analyzer.analyze_commit(
        request.repository,
        request.commit_hash,
        request.diff
    )
    
    # Store in database
    db_record = CommitAnalysis(
        repository=result["repository"],
        commit_hash=result["commit_hash"],
        changed_files=result["changed_files"],
        lines_added=result["lines_added"],
        lines_deleted=result["lines_deleted"],
        risky_patterns=result["risky_patterns"],
        complexity_delta=result["complexity_delta"],
        breaking_change_score=0.0,  # TODO: Calculate from ML model
        semantic_risk_score=result.get("semantic_risk_score"),
        semantic_summary=result.get("semantic_summary")
    )
    db.add(db_record)
    await db.commit()
    
    return CommitAnalysisResponse(**result)


@router.post("/analyze/logs", response_model=LogAnalysisResponse)
async def analyze_logs(
    request: LogAnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze log entries for anomalies and error patterns
    
    - **logs**: List of log entries with level, message, service, etc.
    """
    from src.main import app
    
    analyzer = app.state.log_analyzer
    result = await analyzer.analyze_logs(request.logs)
    
    # Store in database
    db_record = LogAnalysis(
        log_count=result["log_count"],
        error_count=result["error_count"],
        warning_count=result["warning_count"],
        anomalies=result["anomalies"],
        spike_score=result["spike_score"]
    )
    db.add(db_record)
    await db.commit()
    
    return LogAnalysisResponse(**result)


@router.post("/analyze/traces", response_model=TraceAnalysisResponse)
async def analyze_traces(
    request: TraceAnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze distributed traces for performance bottlenecks
    
    - **traces**: List of trace spans
    - **service_name**: Optional filter by service
    """
    from src.main import app
    
    analyzer = app.state.trace_analyzer
    result = await analyzer.analyze_traces(
        request.traces,
        request.service_name
    )
    
    # Store in database
    db_record = TraceAnalysis(
        service_name=request.service_name or "all",
        trace_count=result["trace_count"],
        slow_traces=result["slow_traces"],
        bottlenecks=result["bottlenecks"],
        p95_latency=result["p95_latency"]
    )
    db.add(db_record)
    await db.commit()
    
    return TraceAnalysisResponse(**result)


@router.post("/optimize", response_model=List[OptimizationRecommendation])
async def get_recommendations(
    analysis_results: dict
):
    """
    Generate optimization recommendations based on analysis results
    
    - **analysis_results**: Combined results from various analyzers
    """
    from src.main import app
    
    optimizer = app.state.optimizer
    recommendations = await optimizer.generate_recommendations(analysis_results)
    
    return recommendations
