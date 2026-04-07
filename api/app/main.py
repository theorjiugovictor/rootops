"""
RootOps — FastAPI Application Entry Point

Provides the API surface and orchestrates startup/shutdown lifecycle events.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.concepts import router as concepts_router
from app.api.graph import router as graph_router
from app.api.heal import router as heal_router
from app.api.ingest import router as ingest_router
from app.api.logs import router as logs_router
from app.api.profiles import router as profiles_router
from app.api.query import router as query_router
from app.api.repos import router as repos_router
from app.config import get_settings
from app.db import async_session, get_db, init_db
from app.services.git_ingestor import ingest_repository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

__version__ = "1.0.0"


@asynccontextmanager
async def lifespan(application: FastAPI):  # noqa: ARG001
    """Run startup tasks before the app begins serving requests."""
    # Ensure tables exist (Alembic is preferred for production)
    await init_db()

    # ── Validate embedding model dimension matches DB schema ───────
    # A mismatch (e.g. swapping all-MiniLM-L6-v2 for BGE-M3) silently
    # corrupts vector queries. Fail fast here rather than at query time.
    from app.services.embedding import validate_embedding_dimension
    try:
        validate_embedding_dimension(
            settings.EMBEDDING_MODEL_NAME,
            settings.EMBEDDING_DIMENSION,
        )
    except RuntimeError as exc:
        logger.critical("STARTUP ABORTED — %s", exc)
        raise SystemExit(1) from exc

    # ── Optional: Auto-ingest a repo on startup ─────────────────
    if settings.AUTO_INGEST_REPO_PATH:
        from pathlib import Path
        from app.api.ingest import _set_state

        repo = Path(settings.AUTO_INGEST_REPO_PATH)
        if repo.exists() and (repo / ".git").exists():
            logger.info("Auto-ingesting repo: %s", settings.AUTO_INGEST_REPO_PATH)
            try:
                async with async_session() as session:
                    await _set_state(
                        session,
                        None,  # repo_id resolved after ingest
                        state="running",
                        repo_path=settings.AUTO_INGEST_REPO_PATH,
                        repo_url=None,
                        stats=None,
                        error=None,
                    )
                    stats = await ingest_repository(
                        repo_path=settings.AUTO_INGEST_REPO_PATH,
                        session=session,
                        branch=settings.AUTO_INGEST_BRANCH,
                        max_commits=settings.AUTO_INGEST_MAX_COMMITS,
                    )
                    import uuid as _uuid
                    actual_repo_id = _uuid.UUID(stats["repo_id"])
                    await _set_state(session, actual_repo_id, state="completed", stats=stats)
                logger.info(
                    "Auto-ingest complete: %d commits, %d chunks from %d files",
                    stats.get("commits_ingested", 0),
                    stats.get("chunks_ingested", 0),
                    stats.get("files_processed", 0),
                )
            except Exception:
                logger.exception("Auto-ingest failed")
                async with async_session() as session:
                    await _set_state(session, None, state="failed", error="Auto-ingest failed on startup")
        else:
            logger.warning("AUTO_INGEST_REPO_PATH set but path not found: %s", repo)

    # ── OpenTelemetry log receiver ─────────────────────────────────
    if settings.OTEL_LOGS_RECEIVER_ENABLED:
        logger.info(
            "OTEL log receiver enabled — accepting OTLP/HTTP at POST /v1/logs"
        )
    else:
        logger.info("OTEL log receiver disabled (set OTEL_LOGS_RECEIVER_ENABLED=true to enable)")

    try:
        yield
    finally:
        pass


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "The AI-Native Internal Developer Platform. "
        "RootOps builds a persistent, semantic understanding of your "
        "entire codebase to govern software development from inception."
    ),
    version=__version__,
    lifespan=lifespan,
)

# ── Middleware ───────────────────────────────────────────────────
# Parse the comma-separated CORS_ALLOWED_ORIGINS list.
# Wildcard "*" is kept for convenience only when credentials are NOT needed.
_cors_origins = [o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]
_wildcard_only = _cors_origins == ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    # Credentials (cookies, Authorization header) are incompatible with "*".
    allow_credentials=not _wildcard_only,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routers ──────────────────────────────────────────────────
app.include_router(ingest_router)
app.include_router(logs_router)
app.include_router(query_router)
app.include_router(profiles_router)
app.include_router(heal_router)
app.include_router(repos_router)
app.include_router(concepts_router)
app.include_router(graph_router)


# ── OTLP/HTTP Log Receiver (standard endpoint) ──────────────────
# OpenTelemetry SDKs and Collectors export logs to POST /v1/logs.
# This endpoint is at the root level to comply with the OTLP spec.

from fastapi import Depends, HTTPException, Request  # noqa: E402
from app.db import get_db as _get_db  # noqa: E402
from app.services.otel_collector import ingest_otel_logs  # noqa: E402


@app.post("/v1/logs", tags=["otel"])
async def otlp_logs_receiver(
    request: Request,
    session=Depends(_get_db),
):
    """OTLP/HTTP log receiver — accepts ExportLogsServiceRequest (JSON).

    Point your OpenTelemetry SDK or Collector's OTLP/HTTP exporter at:
        http://<rootops-host>:8000/v1/logs

    Example Collector config:
        exporters:
          otlphttp:
            endpoint: http://rootops-api:8000
            tls:
              insecure: true
    """
    if not settings.OTEL_LOGS_RECEIVER_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="OTEL log receiver is disabled. Set OTEL_LOGS_RECEIVER_ENABLED=true.",
        )

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    try:
        result = await ingest_otel_logs(session, payload)
        # OTLP spec: return empty JSON object on success
        return {}
    except Exception as e:
        logger.exception("OTLP log ingestion failed")
        raise HTTPException(status_code=500, detail=f"OTLP log ingestion failed: {e}")


# ── Routes ───────────────────────────────────────────────────────
@app.get("/health", tags=["ops"])
async def health_check():
    """Readiness probe — confirms the API is alive."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": __version__,
        "llm_backend": settings.LLM_BACKEND,
    }


@app.get("/", tags=["ops"])
async def root():
    """Landing route with a quick summary of the platform."""
    return {
        "app": settings.APP_NAME,
        "version": __version__,
        "description": "AI-Native Internal Developer Platform",
        "docs": "/docs",
        "health": "/health",
    }
