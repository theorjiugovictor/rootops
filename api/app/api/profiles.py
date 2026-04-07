"""
RootOps V2 — Developer Profiles API Router

Endpoints for viewing and building developer coding style profiles
(the "Residency" feature — Developer Pattern Cloning).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.pattern_analyzer import (
    build_developer_profiles,
    get_profile,
    list_profiles,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/profiles", tags=["profiles"])


class ProfileSummary(BaseModel):
    """Summary of a developer profile."""
    author_name: str
    author_email: str
    commit_count: int
    primary_languages: dict | None = None
    summary_preview: str | None = None
    last_updated: str | None = None


class ProfileDetail(BaseModel):
    """Full developer profile."""
    author_name: str
    author_email: str
    pattern_summary: str | None = None
    code_patterns: dict | None = None
    commit_count: int
    files_touched: dict | None = None
    primary_languages: dict | None = None
    last_updated: str | None = None


class BuildProfilesResponse(BaseModel):
    """Response from profile building."""
    status: str
    profiles_built: int
    profiles: list[dict]


@router.get("", response_model=list[ProfileSummary])
async def get_all_profiles(
    session: AsyncSession = Depends(get_db),
):
    """List all developer profiles sorted by commit count."""
    profiles = await list_profiles(session)
    return [ProfileSummary(**p) for p in profiles]


@router.get("/{email}", response_model=ProfileDetail)
async def get_developer_profile(
    email: str,
    session: AsyncSession = Depends(get_db),
):
    """Get a specific developer's coding style profile."""
    profile = await get_profile(email, session)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"No profile found for {email}. Run POST /api/profiles/build first.",
        )
    return ProfileDetail(**profile)


@router.post("/build", response_model=BuildProfilesResponse)
async def trigger_profile_build(
    session: AsyncSession = Depends(get_db),
):
    """Build or update developer profiles from ingested commit data.

    Analyses all ingested code chunks grouped by author, generates
    LLM-powered style summaries, and stores coding fingerprints.
    """
    try:
        profiles = await build_developer_profiles(session)
        return BuildProfilesResponse(
            status="completed",
            profiles_built=len(profiles),
            profiles=profiles,
        )
    except Exception as e:
        logger.exception("Profile building failed")
        raise HTTPException(
            status_code=500,
            detail=f"Profile building failed: {e}",
        )
