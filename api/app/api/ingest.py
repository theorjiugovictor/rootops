"""
RootOps — Ingestion API Router

Endpoints for triggering and monitoring repository ingestion.
Supports both local paths and remote URLs.

Multi-repo: each ingestion creates/updates a Repository row and uses
repo_id as the primary key for IngestionState (not a singleton).
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.code_chunk import CodeChunk
from app.models.commit import Commit
from app.models.ingestion_state import IngestionState
from app.models.repository import Repository
from app.services.git_ingestor import clone_and_ingest, ingest_repository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ingest", tags=["ingestion"])

# ── Legacy singleton used by auto-ingest path ─────────────────────
_LEGACY_REPO_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")


# ── DB helpers ────────────────────────────────────────────────────

async def _get_state(session: AsyncSession, repo_id: uuid.UUID | None = None) -> dict:
    """Read ingestion state for a repo (or the legacy singleton)."""
    pk = repo_id or _LEGACY_REPO_ID
    row = await session.get(IngestionState, pk)
    if row is None:
        return {"state": "idle", "repo_path": None, "repo_url": None, "stats": None, "error": None}
    return row.to_dict()


async def _set_state(
    session: AsyncSession,
    repo_id: uuid.UUID | None = None,
    **fields,
) -> None:
    """Upsert the ingestion state row for a given repo."""
    pk = repo_id or _LEGACY_REPO_ID

    # Ensure the legacy placeholder repository exists before writing state
    if pk == _LEGACY_REPO_ID:
        existing_repo = await session.get(Repository, pk)
        if not existing_repo:
            session.add(Repository(
                id=pk,
                name="legacy",
                description="Auto-created placeholder for single-repo mode.",
            ))
            await session.flush()

    stmt = (
        pg_insert(IngestionState)
        .values(repo_id=pk, **fields)
        .on_conflict_do_update(
            index_elements=["repo_id"],
            set_={**fields},
        )
    )
    await session.execute(stmt)
    await session.commit()


# ── Request / Response models ─────────────────────────────────────

class IngestRequest(BaseModel):
    """Request body for repository ingestion."""
    repo_path: str | None = Field(
        default=None,
        description="Local filesystem path to the git repository.",
    )
    repo_url: str | None = Field(
        default=None,
        description="HTTPS URL of a git repository to clone and ingest.",
    )
    branch: str = Field(default="HEAD", description="Git branch or ref to ingest.")
    max_commits: int | None = Field(
        default=100,
        description="Maximum number of commits to ingest (None = all).",
    )

    # ── Repository metadata ───────────────────────────────────────
    name: str | None = Field(
        default=None,
        description=(
            "Short display name for this repository, e.g. 'payment-service'. "
            "Defaults to the last path component of repo_path/repo_url."
        ),
    )
    team: str | None = Field(
        default=None,
        description="Owning team, e.g. 'payments', 'platform'.",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Free-form tags, e.g. ['python', 'critical-path'].",
    )
    description: str | None = Field(
        default=None,
        description="Short description of what this service does.",
    )

    @model_validator(mode="after")
    def validate_source(self):
        if not self.repo_path and not self.repo_url:
            raise ValueError("Provide either 'repo_path' or 'repo_url'.")
        if self.repo_path and self.repo_url:
            raise ValueError("Provide only one of 'repo_path' or 'repo_url', not both.")
        return self


class IngestResponse(BaseModel):
    status: str
    message: str
    repo_id: str | None = None
    repo_name: str | None = None


class IngestStatusResponse(BaseModel):
    state: str
    repo_path: str | None = None
    repo_url: str | None = None
    stats: dict | None = None
    error: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────

@router.post("", response_model=IngestResponse)
async def trigger_ingestion(
    request: IngestRequest,
    session: AsyncSession = Depends(get_db),
):
    """Trigger ingestion of a git repository.

    Creates/updates a Repository row and tags all chunks and commits with
    its repo_id. Re-ingesting the same repo name updates it in place.
    """
    # Use a transient UUID for state tracking before we know the real repo_id.
    # After ingestion, stats will include the actual repo_id.
    if request.repo_path:
        repo_path = Path(request.repo_path)
        if not repo_path.exists():
            raise HTTPException(400, f"Repository path does not exist: {request.repo_path}")
        if not (repo_path / ".git").exists():
            raise HTTPException(400, f"Not a git repository: {request.repo_path}")

        # Derive repo name early so we can look up existing state
        repo_name = request.name or repo_path.name
        existing_repo = (
            await session.execute(select(Repository).where(Repository.name == repo_name))
        ).scalar_one_or_none()
        repo_id = existing_repo.id if existing_repo else None

        current = await _get_state(session, repo_id)
        if current["state"] == "running":
            raise HTTPException(409, "An ingestion is already in progress for this repository.")

        await _set_state(
            session, repo_id,
            state="running", repo_path=request.repo_path, repo_url=None,
            stats=None, error=None,
        )

        try:
            stats = await ingest_repository(
                repo_path=request.repo_path,
                session=session,
                branch=request.branch,
                max_commits=request.max_commits,
                repo_name=request.name,
                team=request.team,
                tags=request.tags,
                description=request.description,
            )
            actual_repo_id = uuid.UUID(stats["repo_id"])
            await _set_state(session, actual_repo_id, state="completed", stats=stats)
        except Exception as e:
            logger.exception("Ingestion failed")
            await _set_state(session, repo_id, state="failed", error=str(e))
            raise HTTPException(500, f"Ingestion failed: {e}")

    else:
        repo_name = request.name or request.repo_url.rstrip("/").split("/")[-1].removesuffix(".git")
        existing_repo = (
            await session.execute(select(Repository).where(Repository.name == repo_name))
        ).scalar_one_or_none()
        repo_id = existing_repo.id if existing_repo else None

        current = await _get_state(session, repo_id)
        if current["state"] == "running":
            raise HTTPException(409, "An ingestion is already in progress for this repository.")

        await _set_state(
            session, repo_id,
            state="running", repo_path=None, repo_url=request.repo_url,
            stats=None, error=None,
        )

        try:
            stats = await clone_and_ingest(
                repo_url=request.repo_url,
                session=session,
                branch=request.branch,
                max_commits=request.max_commits,
                repo_name=request.name,
                team=request.team,
                tags=request.tags,
                description=request.description,
            )
            actual_repo_id = uuid.UUID(stats["repo_id"])
            await _set_state(session, actual_repo_id, state="completed", stats=stats)
        except Exception as e:
            logger.exception("Ingestion from URL failed")
            await _set_state(session, repo_id, state="failed", error=str(e))
            raise HTTPException(500, f"Ingestion from URL failed: {e}")

    return IngestResponse(
        status="completed",
        repo_id=stats.get("repo_id"),
        repo_name=stats.get("repo_name"),
        message=(
            f"Successfully ingested {stats['commits_ingested']} commits "
            f"and {stats['chunks_ingested']} code chunks "
            f"from {stats['files_processed']} files. "
            f"{stats.get('dependencies_found', 0)} dependency patterns found."
        ),
    )


@router.get("/status", response_model=IngestStatusResponse)
async def get_ingestion_status(
    session: AsyncSession = Depends(get_db),
):
    """Check the current ingestion status (latest / global totals).

    Returns live totals from the database so the dashboard reflects the
    true platform state even after de-duplicated re-ingestion runs.
    """
    total_commits = (await session.execute(select(func.count(Commit.id)))).scalar() or 0
    total_chunks  = (await session.execute(select(func.count(CodeChunk.id)))).scalar() or 0

    # Find the most recently active ingestion state
    latest = (
        await session.execute(
            select(IngestionState).order_by(IngestionState.updated_at.desc()).limit(1)
        )
    ).scalar_one_or_none()

    if latest:
        current = latest.to_dict()
    else:
        current = {"state": "idle", "repo_path": None, "repo_url": None, "stats": None, "error": None}

    last_stats = current.get("stats") or {}
    merged_stats = {
        "commits_ingested": total_commits,
        "chunks_ingested":  total_chunks,
        "files_processed":  last_stats.get("files_processed", 0),
    }

    return IngestStatusResponse(
        state=current["state"],
        repo_path=current.get("repo_path"),
        repo_url=current.get("repo_url"),
        stats=merged_stats,
        error=current.get("error"),
    )
