"""
RootOps — Application Configuration

Reads settings from environment variables (or .env file) using pydantic-settings.
All values have sensible defaults for local Docker Compose usage.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the RootOps application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────
    APP_NAME: str = "RootOps"
    DEBUG: bool = False

    # ── Database ─────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+asyncpg://rootops:rootops_secret@db:5432/rootops"
    )

    # ── Embedding ────────────────────────────────────────────────
    # jinaai/jina-embeddings-v2-base-code: trained on code + English text,
    # 8192-token context, 768-dim. Ideal for mixed code/log corpora.
    # If you change this, also update EMBEDDING_DIMENSION and run migration 0003.
    EMBEDDING_DIMENSION: int = 768
    EMBEDDING_MODEL_NAME: str = "jinaai/jina-embeddings-v2-base-code"

    # ── Reranker ─────────────────────────────────────────────────
    # Cross-encoder reranker: reads query + chunk together for much better
    # precision than bi-encoder similarity alone. Runs on CPU, ~5ms per chunk.
    RERANKER_ENABLED: bool = True
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    # Retrieve this many candidates before reranking down to top_k.
    RERANKER_CANDIDATES: int = 20

    # ── HyDE (Hypothetical Document Embedding) ───────────────────
    # Before embedding a query, ask the LLM to generate a hypothetical code
    # answer, then embed THAT. Searching code-to-code beats question-to-code.
    HYDE_ENABLED: bool = True

    # ── Conversation history ─────────────────────────────────────
    # How many prior turns to include in each LLM call.
    CONVERSATION_HISTORY_TURNS: int = 5

    # ── LLM Backend ─────────────────────────────────────────────
    # Options: "ollama" (default), "openai", "anthropic", "bedrock"
    LLM_BACKEND: str = "ollama"

    # ── Ollama (Local LLM — default, free, no API key) ───────────
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama3"

    # ── OpenAI ───────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # ── Anthropic ────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"

    # ── AWS Bedrock (requires AWS credentials / IAM role) ────────
    BEDROCK_MODEL_ID: str = "us.anthropic.claude-sonnet-4-6"
    BEDROCK_REGION: str = "us-east-1"
    AWS_REGION: str = "us-east-1"

    # ── OpenTelemetry Log Receiver (OTLP/HTTP) ─────────────────
    OTEL_LOGS_RECEIVER_ENABLED: bool = True

    # ── Log Filtering ────────────────────────────────────────────
    # Severity floor: only ingest logs at this level or above.
    # Options: DEBUG, INFO, WARN, ERROR, FATAL  (default: WARN)
    LOG_MIN_SEVERITY: str = "WARN"

    # Service allowlist: comma-separated. Empty = accept all services.
    LOG_ALLOWED_SERVICES: str = ""

    # Dedup window: skip duplicate messages within N seconds (0 = off).
    LOG_DEDUP_WINDOW_SECONDS: int = 60

    # Max message length to embed. Longer messages get truncated.
    LOG_MAX_MESSAGE_LENGTH: int = 2000

    # Max log entries to store per service per hour (0 = unlimited).
    LOG_RATE_LIMIT_PER_SERVICE: int = 500

    # ── RAG / Similarity Thresholds ─────────────────────────────
    # Minimum cosine similarity (0–1) to include a result in query responses.
    # Lower = more results but noisier; higher = fewer but more precise.
    RAG_SIMILARITY_THRESHOLD: float = 0.3

    # Minimum similarity for auto-heal to diagnose an error log against code.
    # Below this the LLM would hallucinate root causes rather than find real ones.
    HEAL_MIN_SIMILARITY: float = 0.25

    # ── CORS ─────────────────────────────────────────────────────
    # Comma-separated list of allowed origins.
    # Defaults to the Next.js UI origin for local Docker Compose usage.
    # Set to "*" only for fully public, credential-free deployments.
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000,http://web:3000"

    # ── GitHub (Auto-Healing PR creation) ────────────────────────
    GITHUB_TOKEN: str = ""
    GITHUB_DEFAULT_REPO: str = ""

    # ── Auto-Ingest on startup (optional) ────────────────────────
    AUTO_INGEST_REPO_PATH: str = ""
    AUTO_INGEST_BRANCH: str = "HEAD"
    AUTO_INGEST_MAX_COMMITS: int = 100

    # ── Multi-Space Embeddings ───────────────────────────────────
    # Separate model for log/doc domain. Defaults to same as code model.
    # Set to e.g. "sentence-transformers/all-MiniLM-L6-v2" for a lighter
    # general-purpose model for log concepts and documentation.
    LOG_EMBEDDING_MODEL_NAME: str = ""  # empty = use EMBEDDING_MODEL_NAME

    # ── Embedding versioning (blue/green index) ──────────────────
    # Bump this when you switch EMBEDDING_MODEL_NAME so new rows are tagged
    # and old rows can be background-migrated without corrupting queries.
    EMBEDDING_MODEL_VERSION: str = "v1"

    # ── Auto-Heal Trust Ladder ───────────────────────────────────
    # Minimum confidence (0–1) to auto-apply a fix to staging.
    HEAL_AUTO_APPLY_MIN_CONFIDENCE: float = 0.80
    # blast_radius threshold: services with > this many downstream deps = "high"
    HEAL_BLAST_RADIUS_HIGH_THRESHOLD: int = 5
    HEAL_BLAST_RADIUS_MEDIUM_THRESHOLD: int = 2

    # ── LogConcept Pipeline ──────────────────────────────────────
    # Drain3 similarity threshold for matching a log to an existing cluster.
    LOG_CONCEPT_DRAIN_SIM_THRESHOLD: float = 0.4
    # Maximum number of LogConcept clusters per service before eviction.
    LOG_CONCEPT_MAX_CLUSTERS: int = 2000
    # Hours of temporal histogram to retain per concept.
    LOG_CONCEPT_HISTOGRAM_HOURS: int = 24

    # ── Query Planner ────────────────────────────────────────────
    # Enable the query classifier and parallel retrieval planner.
    QUERY_PLANNER_ENABLED: bool = True
    # Max graph traversal depth for impact/diagnostic queries.
    QUERY_PLANNER_MAX_GRAPH_DEPTH: int = 3

    # ── Causation Evidence Thresholds ────────────────────────────
    # p-value threshold for Granger causality to promote correlates_with → probable_cause.
    CAUSATION_GRANGER_P_THRESHOLD: float = 0.05
    # Minimum number of incidents before promoting to probable_cause.
    CAUSATION_MIN_INCIDENTS: int = 3


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (reads env once)."""
    return Settings()
