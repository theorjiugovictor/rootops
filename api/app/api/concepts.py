"""
RootOps — LogConcept API Routes

Exposes LogConcept data — pattern-level log understanding — via REST.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.db import get_db
from app.services.log_concept_service import (
    get_concepts_for_service,
    get_rising_concepts,
)

router = APIRouter(prefix="/api/concepts", tags=["concepts"])


@router.get("")
async def list_concepts(
    service: str | None = Query(None, description="Filter by service name"),
    severity: str | None = Query(None, description="Filter by severity (ERROR, WARN, etc.)"),
    limit: int = Query(50, ge=1, le=200),
    session=Depends(get_db),
):
    """List LogConcepts, optionally filtered by service and severity."""
    if service:
        return await get_concepts_for_service(session, service, severity=severity, limit=limit)

    # No service filter — return rising concepts globally
    return await get_rising_concepts(session, limit=limit)


@router.get("/rising")
async def rising_concepts(
    limit: int = Query(20, ge=1, le=100),
    session=Depends(get_db),
):
    """Return LogConcepts currently trending upward (rising)."""
    return await get_rising_concepts(session, limit=limit)
