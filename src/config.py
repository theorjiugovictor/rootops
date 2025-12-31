"""
RootOps Configuration

Environment-based configuration using Pydantic settings.
All settings can be overridden via environment variables or .env file.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """RootOps Configuration Settings"""
    
    # Service Info
    SERVICE_NAME: str = "RootOps Intelligence Engine"
    VERSION: str = "1.0.5"
    
    # Database Configuration
    DATABASE_URL: str = "postgresql://rootops:rootops@postgres:5432/rootops"
    
    # Redis Cache (Optional)
    REDIS_URL: Optional[str] = None
    
    # GitHub Integration (for enriched commit analysis)
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_REPO: Optional[str] = None  # Format: "owner/repo"
    
    # Observability Integrations
    LOKI_URL: Optional[str] = "http://loki:3100"
    PROMETHEUS_URL: Optional[str] = "http://prometheus:9090"
    TEMPO_URL: Optional[str] = "http://tempo:3200"
    
    # ML Model Settings
    MODEL_PATH: str = "/app/models"
    RETRAIN_INTERVAL_HOURS: int = 24
    
    # Analysis Thresholds
    BREAKING_CHANGE_THRESHOLD: float = 0.7
    ANOMALY_THRESHOLD: float = 0.8
    PERFORMANCE_DEGRADATION_THRESHOLD: float = 0.15
    
    # Feature Flags
    ENABLE_BREAKING_CHANGE_DETECTION: bool = True
    ENABLE_ANOMALY_DETECTION: bool = True
    ENABLE_PERFORMANCE_PREDICTION: bool = True
    ENABLE_LLM_ENRICHMENT: bool = False
    
    # Intelligence Engine Settings
    ENABLE_CONTINUOUS_LEARNING: bool = True
    MEMORY_RETENTION_DAYS: int = 365  # How long to keep memories
    PATTERN_CONFIDENCE_THRESHOLD: float = 0.7  # Min confidence to act on patterns
    MIN_SIMILAR_INCIDENTS: int = 3  # Min incidents before pattern is trusted
    
    # Auto-Polling Settings
    ENABLE_AUTO_POLLING: bool = True
    POLL_GITHUB_INTERVAL_SECONDS: int = 300  # Poll GitHub every 5 minutes
    POLL_LOGS_INTERVAL_SECONDS: int = 120  # Monitor logs every 2 minutes
    POLL_METRICS_INTERVAL_SECONDS: int = 60  # Check metrics every minute
    AUTO_ANALYZE_NEW_COMMITS: bool = True  # Automatically analyze new commits
    
    # LLM Security Mode
    LLM_MODE: str = "metadata_only"  # disabled | metadata_only | local | hybrid
    SEND_CODE_TO_LLM: bool = False  # Hard stop on sending actual code
    LOCAL_LLM_URL: Optional[str] = None  # For local LLM mode
    ANONYMIZE_AUTHORS: bool = False  # Hash author names for privacy
    
    # LLM Configuration (Generic)
    LLM_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "gemini"  # gemini | openai | anthropic
    LLM_MODEL: str = "gemini-1.5-flash"
    LLM_MAX_TOKENS: int = 4096
    
    # Advanced Options
    ALLOW_DB_INIT_FAILURE: bool = False
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
