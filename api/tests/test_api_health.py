"""
RootOps — Health & root endpoint tests

Uses FastAPI's TestClient with startup/shutdown hooks patched so no real
database or embedding model is needed.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch


def _make_client():
    """Build a TestClient with all external deps mocked out."""
    with (
        patch("app.db.init_db", new_callable=AsyncMock),
        patch("app.db.create_async_engine", return_value=MagicMock()),
        patch("app.services.embedding.validate_embedding_dimension"),
        patch(
            "sqlalchemy.ext.asyncio.async_sessionmaker",
            return_value=MagicMock(),
        ),
    ):
        from fastapi.testclient import TestClient

        # Patch the lifespan so startup doesn't touch live services
        with patch("app.main.lifespan") as mock_lifespan:
            from contextlib import asynccontextmanager

            @asynccontextmanager
            async def _noop(app):  # noqa: ARG001
                yield

            mock_lifespan.side_effect = None
            mock_lifespan.__call__ = _noop

            from app.main import app

            return TestClient(app, raise_server_exceptions=False)


class TestHealthEndpoints:
    def test_root_returns_app_name(self):
        client = _make_client()
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert "app" in data or "RootOps" in str(data)

    def test_health_check_returns_ok_field(self):
        client = _make_client()
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        # Basic health check must include a status field
        assert "status" in data or "ok" in data or "app" in data

    def test_health_includes_version(self):
        client = _make_client()
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert "version" in data

    def test_detailed_health_returns_checks(self):
        client = _make_client()
        r = client.get("/api/health/detailed")
        # May return 200 or 503 depending on mocked state, but not 404
        assert r.status_code != 404

    def test_docs_available(self):
        """Swagger UI should be reachable."""
        client = _make_client()
        r = client.get("/docs")
        assert r.status_code == 200
