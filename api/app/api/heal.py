"""
RootOps — Auto-Healing API Router

Endpoints for running diagnostics, viewing fix suggestions,
and pushing auto-generated fixes as GitHub Pull Requests.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.github_client import create_fix_pr
from app.services.healer import diagnose, get_fix, get_pending_fixes

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/heal", tags=["auto-healing"])


class DiagnoseResponse(BaseModel):
    """Response from the auto-heal diagnosis."""
    status: str
    diagnoses_count: int
    diagnoses: list[dict]


class FixSummary(BaseModel):
    """Summary of a pending fix."""
    fix_id: str
    error_level: str | None = None
    error_message: str
    error_service: str
    related_file: str
    diagnosis: str


class CreatePRRequest(BaseModel):
    """Request to create a PR from a pending fix."""
    fix_id: str = Field(
        ...,
        description="ID of the pending fix to push as a PR.",
    )
    repo_full_name: str = Field(
        ...,
        description="GitHub repo in 'owner/repo' format.",
        examples=["user/payment-service"],
    )
    new_content: str = Field(
        ...,
        description="The corrected file content to commit.",
    )
    base_branch: str = Field(
        default="main",
        description="Target branch for the PR.",
    )


class CreatePRResponse(BaseModel):
    """Response from PR creation."""
    status: str
    pr_number: int | None = None
    pr_url: str | None = None
    branch: str | None = None
    error: str | None = None


@router.post("", response_model=DiagnoseResponse)
async def run_diagnosis(
    service_name: str | None = Query(
        default=None,
        description="Filter diagnosis to a specific service (e.g. 'payment-service').",
    ),
    session: AsyncSession = Depends(get_db),
):
    """Run auto-healing diagnosis.

    Scans recent error/warning logs, correlates them with ingested code,
    and generates LLM-powered root cause analysis and fix suggestions.

    Use `service_name` to restrict diagnosis to a single service's logs.
    """
    try:
        diagnoses = await diagnose(session, service_name=service_name)
        return DiagnoseResponse(
            status="completed",
            diagnoses_count=len(diagnoses),
            diagnoses=diagnoses,
        )
    except Exception as e:
        logger.exception("Diagnosis failed")
        raise HTTPException(
            status_code=500,
            detail=f"Diagnosis failed: {e}",
        )


@router.get("/fixes", response_model=list[dict])
async def list_fixes(session: AsyncSession = Depends(get_db)):
    """List all pending fix suggestions from previous diagnoses."""
    return await get_pending_fixes(session)


@router.get("/fixes/{fix_id}")
async def get_fix_detail(fix_id: str, session: AsyncSession = Depends(get_db)):
    """Get details of a specific pending fix."""
    fix = await get_fix(session, fix_id)
    if not fix:
        raise HTTPException(
            status_code=404,
            detail=f"Fix '{fix_id}' not found. Run POST /api/heal first.",
        )
    return fix


@router.post("/pr", response_model=CreatePRResponse)
async def create_pr(
    request: CreatePRRequest,
    session: AsyncSession = Depends(get_db),
):
    """Push a pending fix as a GitHub Pull Request.

    Takes a fix_id from a previous diagnosis, the corrected code,
    and creates a branch + PR on the specified GitHub repository.
    """
    fix = await get_fix(session, request.fix_id)
    if not fix:
        raise HTTPException(
            status_code=404,
            detail=f"Fix '{request.fix_id}' not found. Run POST /api/heal first.",
        )

    try:
        result = await create_fix_pr(
            repo_full_name=request.repo_full_name,
            file_path=fix["related_file"],
            new_content=request.new_content,
            fix_title=fix["error_message"][:100],
            fix_description=fix["diagnosis"],
            base_branch=request.base_branch,
        )
        return CreatePRResponse(
            status="created",
            pr_number=result["pr_number"],
            pr_url=result["pr_url"],
            branch=result["branch"],
        )
    except Exception as e:
        logger.exception("PR creation failed")
        return CreatePRResponse(
            status="failed",
            error=str(e),
        )
