"""
RootOps — Pytest Configuration & Shared Fixtures

Provides reusable fixtures for testing services without requiring a live
database, Ollama instance, or HuggingFace embedding model download.

Design:
  - All heavy external dependencies (DB, LLM, embeddings) are mocked.
  - Tests that need the FastAPI app use a lightweight TestClient with
    lifespan hooks patched out.
  - Async tests use anyio (via pytest-anyio) with asyncio backend.
"""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession


# ── Async backend ─────────────────────────────────────────────────

@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


# ── Mock database session ─────────────────────────────────────────

@pytest.fixture
def mock_session() -> MagicMock:
    """Return a MagicMock that satisfies AsyncSession's interface."""
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    return session


# ── Mock embedding ────────────────────────────────────────────────

FAKE_EMBEDDING = [0.01] * 768  # 768-dim zero vector


@pytest.fixture
def mock_embed_text():
    """Patch embed_text to return a deterministic fake embedding."""
    with patch(
        "app.services.rag_engine.embed_text",
        new_callable=lambda: lambda *a, **kw: asyncio.coroutine(lambda: FAKE_EMBEDDING)(),
    ):
        yield


# ── Mock LLM backend ──────────────────────────────────────────────

@pytest.fixture
def mock_llm_generate():
    """Patch the LLM generate function to return a canned answer."""
    with patch(
        "app.services.llm_backend.generate",
        new_callable=AsyncMock,
        return_value="Mocked LLM answer for testing.",
    ) as mock:
        yield mock


# ── FastAPI TestClient (no lifespan) ─────────────────────────────

@pytest.fixture(scope="module")
def test_client():
    """
    Return an httpx TestClient for the FastAPI app.

    Patches out the lifespan startup hooks so no DB / embedding model
    is required during tests.  Service calls are still live — mock them
    inside individual tests as needed.
    """
    with (
        patch("app.db.init_db", new_callable=AsyncMock),
        patch("app.services.embedding.validate_embedding_dimension"),
        patch("sqlalchemy.ext.asyncio.create_async_engine"),
    ):
        from fastapi.testclient import TestClient
        from app.main import app

        # Override lifespan so startup doesn't try to touch real services
        app.router.lifespan_context = None  # type: ignore[attr-defined]

        with TestClient(app, raise_server_exceptions=True) as client:
            yield client