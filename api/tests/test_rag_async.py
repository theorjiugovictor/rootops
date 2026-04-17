"""
RootOps — Async RAG engine tests

Tests the query_codebase() pipeline with mocked DB and embedding functions.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


FAKE_VEC = [0.01] * 768


class TestQueryCodebase:
    @pytest.mark.anyio
    async def test_returns_structured_result(self):
        """query_codebase() always returns the expected keys."""
        mock_session = AsyncMock()

        # DB returns no matching chunks
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        with (
            patch("app.services.rag_engine.embed_text", new_callable=AsyncMock, return_value=FAKE_VEC),
            patch("app.services.rag_engine.settings") as mock_cfg,
        ):
            mock_cfg.RAG_SIMILARITY_THRESHOLD = 0.3
            mock_cfg.RERANKER_ENABLED = False
            mock_cfg.RERANKER_CANDIDATES = 20
            mock_cfg.HYDE_ENABLED = False
            mock_cfg.LLM_AVAILABLE = False
            mock_cfg.QUERY_PLANNER_ENABLED = False

            from app.services.rag_engine import query_codebase

            result = await query_codebase("what is auth?", mock_session, use_llm=False)

        assert isinstance(result, dict)
        assert "answer" in result
        assert "sources" in result
        assert "log_matches" in result
        assert "metadata" in result

    @pytest.mark.anyio
    async def test_no_context_returns_helpful_message(self):
        """Without any matching chunks, the answer guides the user."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        with (
            patch("app.services.rag_engine.embed_text", new_callable=AsyncMock, return_value=FAKE_VEC),
            patch("app.services.rag_engine.settings") as mock_cfg,
        ):
            mock_cfg.RAG_SIMILARITY_THRESHOLD = 0.3
            mock_cfg.RERANKER_ENABLED = False
            mock_cfg.RERANKER_CANDIDATES = 20
            mock_cfg.HYDE_ENABLED = False
            mock_cfg.LLM_AVAILABLE = False
            mock_cfg.QUERY_PLANNER_ENABLED = False

            from app.services.rag_engine import query_codebase

            result = await query_codebase("mystery function?", mock_session, use_llm=False)

        # Answer should guide user, not raise an exception
        assert isinstance(result["answer"], str)
        assert len(result["answer"]) > 0

    @pytest.mark.anyio
    async def test_similarity_threshold_applied(self):
        """Chunks below the threshold should be filtered out."""
        mock_session = AsyncMock()

        # Return a row with a very low similarity score
        low_sim_row = MagicMock()
        low_sim_row.similarity = 0.05  # below default 0.3 threshold
        low_sim_row.file_path = "app/auth.py"
        low_sim_row.chunk_content = "def login(): pass"
        low_sim_row.start_line = 1
        low_sim_row.end_line = 5
        low_sim_row.language = "python"
        low_sim_row.commit_sha = "abc123"
        low_sim_row.repo_id = None

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [low_sim_row]
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        with (
            patch("app.services.rag_engine.embed_text", new_callable=AsyncMock, return_value=FAKE_VEC),
            patch("app.services.rag_engine.settings") as mock_cfg,
        ):
            mock_cfg.RAG_SIMILARITY_THRESHOLD = 0.3
            mock_cfg.RERANKER_ENABLED = False
            mock_cfg.RERANKER_CANDIDATES = 20
            mock_cfg.HYDE_ENABLED = False
            mock_cfg.LLM_AVAILABLE = False
            mock_cfg.QUERY_PLANNER_ENABLED = False

            from app.services.rag_engine import query_codebase

            result = await query_codebase("auth?", mock_session, use_llm=False)

        # The low-similarity chunk must be filtered
        assert result["metadata"]["chunks_retrieved"] == 0
        assert len(result["sources"]) == 0
