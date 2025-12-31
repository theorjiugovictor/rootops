"""
Database models for persisting analysis results and building long-term memory
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean, Text
from sqlalchemy.sql import func
from src.database import Base


class CommitAnalysis(Base):
    """Store commit analysis results (deprecated - use CommitMemory)"""
    __tablename__ = "commit_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    repository = Column(String, index=True)
    commit_hash = Column(String, index=True)
    changed_files = Column(Integer)
    lines_added = Column(Integer)
    lines_deleted = Column(Integer)
    risky_patterns = Column(JSON)
    complexity_delta = Column(Float)
    breaking_change_score = Column(Float)
    semantic_risk_score = Column(Float, nullable=True)
    semantic_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# Intelligence Engine Memory Models

class CommitMemory(Base):
    """
    Long-term memory of all commits analyzed.
    The engine never forgets a commit.
    """
    __tablename__ = "commit_memory"
    
    id = Column(Integer, primary_key=True, index=True)
    sha = Column(String, index=True, unique=True)
    repository = Column(String, index=True)
    author = Column(String, index=True)
    author_email = Column(String, index=True)
    files_changed = Column(Integer)
    files = Column(JSON)  # List of filenames modified
    lines_added = Column(Integer)
    lines_deleted = Column(Integer)
    risk_score = Column(Float, index=True)
    complexity_score = Column(Float)
    blast_radius = Column(Integer)
    test_ratio = Column(Float)
    commit_type = Column(String, index=True)  # bugfix, feature, refactor, etc
    risky_patterns = Column(JSON)  # List of detected patterns
    prediction_details = Column(JSON) # Detailed ML predictions (e.g. latency)
    committed_at = Column(DateTime(timezone=True), index=True)
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())


class DeploymentEvent(Base):
    """
    Memory of all deployments and their predictions.
    Links commits to production outcomes.
    """
    __tablename__ = "deployment_events"
    
    id = Column(Integer, primary_key=True, index=True)
    deployment_id = Column(String, index=True, unique=True)
    commit_sha = Column(String, index=True)
    repository = Column(String, index=True)
    deployed_at = Column(DateTime(timezone=True), index=True)
    predicted_risk = Column(Float)  # What we predicted
    predicted_impact = Column(String)  # CRITICAL, HIGH, MEDIUM, LOW
    recommended_action = Column(String)  # BLOCK, STAGED_ROLLOUT, PROCEED
    system_state = Column(JSON)  # System health at deployment time
    resulted_in_incident = Column(Boolean, default=False, index=True)
    incident_id = Column(String, nullable=True)
    time_to_incident_minutes = Column(Integer, nullable=True)


class IncidentMemory(Base):
    """
    Memory of all incidents.
    The engine learns from every failure.
    """
    __tablename__ = "incident_memory"
    
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(String, index=True, unique=True)
    severity = Column(String, index=True)  # P1, P2, P3, P4
    description = Column(Text)
    root_cause_commit = Column(String, index=True, nullable=True)
    occurred_at = Column(DateTime(timezone=True), index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    time_to_detect_minutes = Column(Integer)
    time_to_resolve_minutes = Column(Integer, nullable=True)
    patterns = Column(JSON)  # Patterns involved
    affected_services = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PatternMemory(Base):
    """
    Learned patterns that indicate risk.
    Continuously updated with new evidence.
    """
    __tablename__ = "pattern_memory"
    
    id = Column(Integer, primary_key=True, index=True)
    pattern_type = Column(String, index=True, unique=True)  # auth_logic, db_migration, etc
    description = Column(Text)
    occurrence_count = Column(Integer, default=0)
    incident_count = Column(Integer, default=0)
    confidence = Column(Float, index=True)  # 0-1, how confident we are this causes issues
    typical_impact = Column(String)  # CRITICAL, HIGH, MEDIUM, LOW
    first_seen = Column(DateTime(timezone=True))
    last_seen = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CorrelationLearning(Base):
    """
    Learned correlations between events.
    E.g., "Commits to auth/ by junior devs on Fridays → incidents"
    """
    __tablename__ = "correlation_learning"
    
    id = Column(Integer, primary_key=True, index=True)
    correlation_key = Column(String, index=True, unique=True)  # Hash of correlation factors
    description = Column(Text)
    factors = Column(JSON)  # What factors are involved
    occurrence_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    confidence = Column(Float, index=True)
    strength = Column(Float)  # How strong the correlation is
    discovered_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class LogAnalysis(Base):
    """Store log analysis results"""
    __tablename__ = "log_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    log_count = Column(Integer)
    error_count = Column(Integer)
    warning_count = Column(Integer)
    anomalies = Column(JSON)
    spike_score = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TraceAnalysis(Base):
    """Store trace analysis results"""
    __tablename__ = "trace_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String, index=True)
    trace_count = Column(Integer)
    slow_traces = Column(JSON)
    bottlenecks = Column(JSON)
    p95_latency = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class OptimizationRecord(Base):
    """Store optimization recommendations"""
    __tablename__ = "optimizations"
    
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String)
    severity = Column(String, index=True)
    title = Column(String)
    description = Column(Text)
    impact = Column(String)
    auto_fixable = Column(Boolean)
    applied = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
