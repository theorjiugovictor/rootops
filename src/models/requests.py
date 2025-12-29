"""
Pydantic request/response models for API endpoints
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class CommitAnalysisRequest(BaseModel):
    """Request for commit analysis"""
    repository: str = Field(..., description="Repository name")
    commit_hash: str = Field(..., description="Commit hash or reference")
    diff: Optional[str] = Field(None, description="Optional commit diff for LLM enrichment")


class CommitAnalysisResponse(BaseModel):
    """Response from commit analysis"""
    repository: str
    commit_hash: str
    changed_files: int
    lines_added: int
    lines_deleted: int
    risky_patterns: List[str]
    complexity_delta: float
    risk_score: Optional[float] = None
    blast_radius: Optional[int] = None
    test_ratio: Optional[float] = None
    commit_type: Optional[str] = None
    author: Optional[str] = None
    author_commits_90d: Optional[int] = None
    author_avg_files: Optional[float] = None
    semantic_risk_score: Optional[float] = None
    semantic_summary: Optional[str] = None
    timestamp: str


class LogAnalysisRequest(BaseModel):
    """Request for log analysis"""
    logs: List[Dict[str, Any]] = Field(..., description="List of log entries")
    time_range: Optional[Dict[str, str]] = Field(None, description="Time range filter")


class LogAnalysisResponse(BaseModel):
    """Response from log analysis"""
    log_count: int
    error_count: int
    warning_count: int
    anomalies: List[Dict[str, Any]]
    spike_score: float
    timestamp: str


class TraceAnalysisRequest(BaseModel):
    """Request for trace analysis"""
    traces: List[Dict[str, Any]] = Field(..., description="List of trace spans")
    service_name: Optional[str] = Field(None, description="Filter by service")


class TraceAnalysisResponse(BaseModel):
    """Response from trace analysis"""
    trace_count: int
    slow_traces: List[Dict[str, Any]]
    bottlenecks: List[Dict[str, Any]]
    p95_latency: float
    timestamp: str


class OptimizationRecommendation(BaseModel):
    """Optimization recommendation"""
    type: str
    severity: str
    title: str
    description: str
    impact: str
    auto_fixable: bool
    implementation: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    components: Dict[str, str]


# Intelligence Engine Models

class IntelligenceRequest(BaseModel):
    """Request for comprehensive intelligence analysis"""
    commit_sha: str = Field(..., description="Commit hash to analyze")
    repository: str = Field(..., description="Repository name")
    deployment_id: Optional[str] = Field(None, description="Optional deployment identifier")


class IntelligenceResponse(BaseModel):
    """Comprehensive intelligence response"""
    commit_sha: str
    repository: str
    analysis: Dict[str, Any]
    system_state: Dict[str, Any]
    intelligence: Dict[str, Any]
    prediction: Dict[str, Any]
    recommendations: List[str]
    action: str
    monitoring: Dict[str, Any]
    learned_from: str


class IncidentRecordRequest(BaseModel):
    """Request to record an incident for learning"""
    incident_id: str = Field(..., description="Unique incident identifier")
    severity: str = Field(..., description="P1, P2, P3, or P4")
    description: str = Field(..., description="What happened")
    root_cause_commit: Optional[str] = Field(None, description="Commit that caused the incident")
    patterns: Optional[List[str]] = Field(None, description="List of patterns involved")


class DeploymentMonitorRequest(BaseModel):
    """Request to monitor deployment health"""
    deployment_id: str = Field(..., description="Deployment identifier to monitor")
    current_logs: List[Dict[str, Any]] = Field(..., description="Recent logs from the system")
    duration_minutes: int = Field(30, description="How long deployment has been running")
