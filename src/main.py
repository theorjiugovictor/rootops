"""
RootOps Intelligence Engine

AI-powered DevOps intelligence platform for predictive insights.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import asyncio
from datetime import datetime, timezone

from src.config import settings
from src.database import init_db, get_db
from src.models.predictions import BreakingChangeDetector, AnomalyDetector, PerformancePredictor
from src.services import CommitAnalyzer, LogAnalyzer, TraceAnalyzer, Optimizer
from src.services.github_enrichment import GitHubEnrichmentService
from src.services.intelligence_engine import IntelligenceEngine
from src.services.auto_poller import AutoPoller
from src.monitoring import setup_monitoring
from src.api import router
from src.api.dashboard_routes import router as dashboard_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.VERSION}...")
    
    # Initialize database
    try:
        await init_db()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        if not settings.ALLOW_DB_INIT_FAILURE:
            raise
    
    # Initialize ML models
    logger.info("Loading ML models...")
    app.state.breaking_change_detector = BreakingChangeDetector()
    app.state.anomaly_detector = AnomalyDetector()
    app.state.performance_predictor = PerformancePredictor()
    
    # Initialize services
    logger.info("Initializing services...")
    app.state.commit_analyzer = CommitAnalyzer()
    app.state.log_analyzer = LogAnalyzer()
    app.state.trace_analyzer = TraceAnalyzer()
    app.state.optimizer = Optimizer()
    
    # Initialize GitHub enrichment service
    app.state.github_service = GitHubEnrichmentService()
    
    # Initialize Intelligence Engine (the brain)
    logger.info("Initializing Intelligence Engine - The Brain That Never Forgets...")
    # Note: Intelligence Engine needs a db session, we'll handle this in routes
    app.state.intelligence_engine_factory = lambda db_session: IntelligenceEngine(
        db_session=db_session,
        github_service=app.state.github_service,
        log_analyzer=app.state.log_analyzer,
        trace_analyzer=app.state.trace_analyzer
    )
    
    # Start auto-polling background workers
    logger.info("Starting background auto-polling workers...")
    app.state.auto_poller = AutoPoller()
    poller_task = asyncio.create_task(app.state.auto_poller.start())
    
    logger.info(f"{settings.SERVICE_NAME} started successfully!")
    logger.info("Auto-polling GitHub commits and monitoring logs...")
    logger.info("Dashboard available at http://localhost:8000/dashboard")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.SERVICE_NAME}...")
    await app.state.auto_poller.stop()
    poller_task.cancel()
    try:
        await poller_task
    except asyncio.CancelledError:
        pass


# Create FastAPI application
app = FastAPI(
    title="RootOps Intelligence Engine",
    description="""
    AI-powered DevOps intelligence platform that analyzes commits, logs, and traces
    to provide predictive insights and optimization recommendations.
    
    ## Features
    
    * **Commit Analysis** - Detect breaking changes before deployment
    * **Log Analysis** - Identify anomalies and error patterns
    * **Trace Analysis** - Find performance bottlenecks
    * **Optimization** - Get AI-powered recommendations
    
    ## Quick Start
    
    ```bash
    docker run -p 8000:8000 rootops/rootops
    ```
    
    Access the API at http://localhost:8000
    """,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup monitoring
setup_monitoring(app)

# Include API routes
app.include_router(router, prefix="/api/v1", tags=["analysis"])
app.include_router(dashboard_router)

# Mount static files for dashboard
app.mount("/dashboard", StaticFiles(directory="src/static", html=True), name="static")


@app.get("/")
async def root():
    """Root endpoint - service information"""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs",
        "metrics": "/metrics",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "database": "connected",
            "ml_models": "loaded",
            "services": "ready"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
