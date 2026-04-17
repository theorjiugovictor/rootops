"""
RootOps — Async healer tests

Tests the diagnose() function with fully mocked DB and LLM dependencies.
Uses pytest-anyio for async test execution.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestDiagnoseGuards:
    @pytest.mark.anyio
    async def test_returns_error_dict_when_llm_unavailable(self):
        """diagnose() returns a helpful message instead of crashing when LLM is off."""
        mock_session = AsyncMock()

        with patch("app.services.healer.settings") as mock_settings:
            mock_settings.LLM_AVAILABLE = False
            mock_settings.LLM_BACKEND = "openai"

            from app.services.healer import diagnose

            result = await diagnose(mock_session)

        assert len(result) == 1
        assert "error" in result[0]
        assert "API key" in result[0]["error"] or "LLM" in result[0]["error"]

    @pytest.mark.anyio
    async def test_returns_empty_when_no_error_logs(self):
        """diagnose() returns [] when no ERROR/WARN logs exist."""
        mock_session = AsyncMock()

        # Simulate empty log query result
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_execute_result)
        mock_session.commit = AsyncMock()

        with patch("app.services.healer.settings") as mock_settings:
            mock_settings.LLM_AVAILABLE = True
            mock_settings.LLM_BACKEND = "openai"
            mock_settings.HEAL_MIN_SIMILARITY = 0.25
            mock_settings.HEAL_AUTO_APPLY_MIN_CONFIDENCE = 0.8
            mock_settings.HEAL_BLAST_RADIUS_HIGH_THRESHOLD = 5
            mock_settings.HEAL_BLAST_RADIUS_MEDIUM_THRESHOLD = 2

            from app.services.healer import diagnose

            result = await diagnose(mock_session)

        assert result == []


class TestBlastRadiusComputation:
    @pytest.mark.anyio
    async def test_no_downstream_services_is_low(self):
        from app.services.healer import _compute_blast_radius

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 0
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.healer.settings") as s:
            s.HEAL_BLAST_RADIUS_HIGH_THRESHOLD = 5
            s.HEAL_BLAST_RADIUS_MEDIUM_THRESHOLD = 2

            count, level = await _compute_blast_radius(mock_session, "my-service")

        assert count == 0
        assert level == "low"

    @pytest.mark.anyio
    async def test_many_downstream_is_high(self):
        from app.services.healer import _compute_blast_radius

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 10
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.healer.settings") as s:
            s.HEAL_BLAST_RADIUS_HIGH_THRESHOLD = 5
            s.HEAL_BLAST_RADIUS_MEDIUM_THRESHOLD = 2

            count, level = await _compute_blast_radius(mock_session, "central-service")

        assert count == 10
        assert level == "high"
